"""Measured laptop storage/processing and independent Spark MLlib demonstration."""
import gc,json,os,time,platform
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import polars as pl
from .pipeline import ROOT,read_financials,dev_labels,dump_json

def run_benchmarks(run_spark=True):
    out=ROOT/'data/benchmark';out.mkdir(parents=True,exist_ok=True)
    cols=['CERT','REPDTE','ASSET','EQ','LNLSGR','NCLNLS','NETINC']
    f=read_financials(date(2011,9,30)).select(cols).sort('CERT','REPDTE')
    f.write_csv(out/'financials.csv');f.write_parquet(out/'financials.parquet',compression='zstd')
    results=[];shape=f.shape;del f;gc.collect()
    def measure(label,fn):
        ts=[]
        for rep in range(3):
            gc.collect();t=time.perf_counter();v=fn();ts.append(time.perf_counter()-t)
            if rep<2:del v
        results.append({'operation':label,'median_seconds':float(np.median(ts)),'min_seconds':min(ts),'runs':3,'rows':shape[0],'columns':shape[1],'cache':'warm OS-cache; no claim of cold disk reads'})
        return v
    pq=out/'financials.parquet';csv=out/'financials.csv'
    a=measure('pandas CSV full read',lambda:pd.read_csv(csv,dtype={'REPDTE':str}));del a
    a=measure('pandas Parquet full read',lambda:pd.read_parquet(pq));del a
    a=measure('Polars Parquet full read',lambda:pl.read_parquet(pq));del a
    a=measure('Polars Parquet projected read',lambda:pl.read_parquet(pq,columns=['CERT','ASSET']));del a
    def polars_query():
        f=pl.scan_parquet(pq).with_columns(qi=pl.col('REPDTE').str.slice(0,4).cast(pl.Int64)*4+(pl.col('REPDTE').str.slice(4,2).cast(pl.Int64)-1)//3)
        prev=f.select('CERT',(pl.col('qi')+1).alias('qi'),pl.col('NETINC').alias('prev_netinc'))
        return (f.join(prev,on=['CERT','qi'],how='left').with_columns(eq_assets=pl.when(pl.col('ASSET')>0).then(100*pl.col('EQ')/pl.col('ASSET')),npl=pl.when(pl.col('LNLSGR')>0).then(100*pl.col('NCLNLS')/pl.col('LNLSGR')),flow=pl.when(pl.col('REPDTE').str.slice(4,2)=='03').then(pl.col('NETINC')).otherwise(pl.col('NETINC')-pl.col('prev_netinc'))).group_by('REPDTE').agg(pl.len().alias('rows'),pl.col('eq_assets').mean(),pl.col('npl').mean(),pl.col('flow').sum()).sort('REPDTE'))
    def pandas_query():
        f=pd.read_parquet(pq);f['qi']=f.REPDTE.str[:4].astype(int)*4+(f.REPDTE.str[4:6].astype(int)-1)//3
        prev=f[['CERT','qi','NETINC']].rename(columns={'NETINC':'prev_netinc'});prev['qi']+=1
        f=f.merge(prev,on=['CERT','qi'],how='left',validate='one_to_one')
        f['eq_assets']=np.where(f.ASSET>0,100*f.EQ/f.ASSET,np.nan);f['npl']=np.where(f.LNLSGR>0,100*f.NCLNLS/f.LNLSGR,np.nan)
        f['flow']=np.where(f.REPDTE.str[4:6]=='03',f.NETINC,f.NETINC-f.prev_netinc)
        return f.groupby('REPDTE',as_index=False).agg(rows=('CERT','size'),eq_assets=('eq_assets','mean'),npl=('npl','mean'),flow=('flow','sum')).sort_values('REPDTE')
    (ROOT/'reports/polars_plan.txt').write_text(polars_query().explain(optimized=True).replace(str(ROOT),'<PROJECT_ROOT>'))
    pol=measure('Polars lazy scan + exact-quarter join + ratios + aggregate',lambda:polars_query().collect()).to_pandas()
    pan=measure('pandas scan + exact-quarter join + ratios + aggregate',pandas_query)
    for c in ['rows','eq_assets','npl','flow']:assert np.allclose(pol[c],pan[c],rtol=1e-10,atol=1e-7,equal_nan=True),c
    pd.DataFrame(results).to_csv(ROOT/'reports/tables/storage_processing_benchmarks.csv',index=False)
    dump_json(ROOT/'reports/tables/storage_sizes.json',{'rows':shape[0],'columns':shape[1],'csv_bytes':csv.stat().st_size,'parquet_zstd_bytes':pq.stat().st_size,'ratio_csv_to_parquet':csv.stat().st_size/pq.stat().st_size,'scope':'Financials 1984Q1-2011Q3; fixed 7-column projection, not all 87 fields','machine':platform.platform(),'logical_cpus':os.cpu_count(),'comparison':'same rows and columns; CSV dtypes provided; warm cache, 3 runs'})
    if run_spark:spark_demo(pq,pol)
    return pd.DataFrame(results)

def spark_demo(parquet_path,polars_result):
    import sys
    conda_jvm=Path(sys.prefix)/'lib/jvm'
    if conda_jvm.exists():os.environ.setdefault('JAVA_HOME',str(conda_jvm))
    os.environ.setdefault('SPARK_LOCAL_IP','127.0.0.1')
    from pyspark.sql import SparkSession,functions as F
    from pyspark.ml import Pipeline
    from pyspark.ml.feature import Imputer,VectorAssembler,StandardScaler
    from pyspark.ml.classification import LogisticRegression
    from sklearn.metrics import average_precision_score,roc_auc_score
    spark=SparkSession.builder.master('local[2]').appName('FDIC-portfolio').config('spark.driver.memory','2g').config('spark.sql.shuffle.partitions','4').config('spark.driver.bindAddress','127.0.0.1').config('spark.ui.enabled','false').getOrCreate()
    spark.sparkContext.setLogLevel('ERROR')
    f=spark.read.parquet(str(parquet_path)).withColumn('qi',F.substring('REPDTE',1,4).cast('long')*4+F.floor((F.substring('REPDTE',5,2).cast('int')-1)/3))
    prev=f.select('CERT',(F.col('qi')+1).alias('qi'),F.col('NETINC').alias('prev_netinc'))
    query=f.join(prev,['CERT','qi'],'left').withColumn('eq_assets',F.when(F.col('ASSET')>0,100*F.col('EQ')/F.col('ASSET'))).withColumn('npl',F.when(F.col('LNLSGR')>0,100*F.col('NCLNLS')/F.col('LNLSGR'))).withColumn('flow',F.when(F.substring('REPDTE',5,2)=='03',F.col('NETINC')).otherwise(F.col('NETINC')-F.col('prev_netinc'))).groupBy('REPDTE').agg(F.count('*').alias('rows'),F.avg('eq_assets').alias('eq_assets'),F.avg('npl').alias('npl'),F.sum('flow').alias('flow')).orderBy('REPDTE')
    t=time.perf_counter();got=query.toPandas();seconds=time.perf_counter()-t
    differences=[]
    for c in ['rows','eq_assets','npl','flow']:
        ok=np.allclose(got[c],polars_result[c],rtol=1e-10,atol=1e-7,equal_nan=True);assert ok,c
        differences.append({'column':c,'match':bool(ok),'max_abs_diff':float(np.nanmax(np.abs(got[c]-polars_result[c])))})
    pd.DataFrame(differences).to_csv(ROOT/'reports/tables/spark_parity.csv',index=False)
    (ROOT/'reports/spark_plan.txt').write_text(__import__('re').sub(r'file:/[^,\]\n]+','file:<PRIVATE_DATA_LOCATION>',query._jdf.queryExecution().toString()).replace(str(ROOT),'<PROJECT_ROOT>'))
    path=ROOT/'data/processed/features_to_2011-09-30.parquet'
    core=['eq_assets','noncurrent_loans','reserve_loans','roa_ttm','loans_deposits','borrowed_assets','log_assets']
    data=pl.read_parquet(path).join(dev_labels(),on=['CERT','report_period_end'],how='inner').filter(~pl.col('fit_exclude_i01')).select('prediction_as_of','y_audit',*core)
    # CSV ingestion avoids pandas timezone/Arrow differences across Spark installations.
    dp=ROOT/'data/benchmark/mllib_input.csv';data.write_csv(dp)
    sdf=spark.read.option('header',True).option('inferSchema',True).csv(str(dp)).withColumn('label',F.col('y_audit').cast('double'))
    train=sdf.filter(F.col('prediction_as_of')<='2009-12-31');val=sdf.filter((F.col('prediction_as_of')>='2011-01-01')&(F.col('prediction_as_of')<='2011-12-31'))
    # Demonstration only: train-fitted median, scaling and regularized LR. Not the historical sklearn recipe.
    imp=Imputer(inputCols=core,outputCols=[c+'_imp' for c in core],strategy='median')
    vec=VectorAssembler(inputCols=[c+'_imp' for c in core],outputCol='features_raw')
    scale=StandardScaler(inputCol='features_raw',outputCol='features',withMean=True,withStd=True)
    lr=LogisticRegression(maxIter=80,regParam=.1,elasticNetParam=0.,labelCol='label',featuresCol='features')
    t=time.perf_counter();model=Pipeline(stages=[imp,vec,scale,lr]).fit(train)
    preds=model.transform(val).select('label','probability').collect();secs=time.perf_counter()-t
    y=np.array([x.label for x in preds]);s=np.array([float(x.probability[1]) for x in preds]);assert np.isfinite(s).all()
    dump_json(ROOT/'reports/tables/spark_mllib_demo.json',{'spark_version':spark.version,'master':'local[2]','spark_query_seconds_startup_excluded':seconds,'fit_and_score_seconds':secs,'train_end':'2009-12-31','label_maturity_before_validation':True,'validation_year':2011,'validation_rows':len(y),'positive_rows':int(y.sum()),'AP':float(average_precision_score(y,s)),'ROC_AUC':float(roc_auc_score(y,s)),'maxIter':80,'regParam':.1,'note':'separate demonstration baseline; Spark approximate median and regularization differ from sklearn; not used for model selection','parity':'Polars, pandas and Spark query outputs numerically agree'})
    spark.stop()
