import numpy as np
import pandas as pd

import sys
from os.path import join as opj

from fg_shared import _fg_data

data_folder = opj(_fg_data, 'SEATRAC/TB_hackday_2023/data/darrah_etal')
bigdata_folder = opj(_fg_data, 'SEATRAC/TB_hackday_2023/bigdata')

def make_pseudo_bulk(downsamples=1000):
    """Meta-data file contains cell-level data for Week 13 and Week 25

    NOTE: the meta-data and cts data are not aligned by cellID so a MERGE is neccessary on md['NAME'] and cts columns"""
    md = pd.read_csv(opj(data_folder, 'updated_alexandria_metadata.txt'), sep='\t', low_memory=False)
    md = md.iloc[1:]

    """Clustering is provided separately for the Wk13 and Wk25 data"""
    clust = pd.read_csv(opj(data_folder, 'week13_clusters.txt'), sep='\t')
    clust = clust.iloc[1:]
    clust = clust.assign(X_13=clust['X'].astype(float),
                         Y_13=clust['Y'].astype(float))

    md = pd.merge(md, clust[['NAME', 'X_13', 'Y_13']], on='NAME', how='left')

    clust = pd.read_csv(opj(data_folder, 'week25_clusters.txt'), sep='\t')
    clust = clust.iloc[1:]
    clust = clust.assign(X_25=clust['X'].astype(float),
                         Y_25=clust['Y'].astype(float))

    """Merging here will create NA missing values for the cells that were not clustered and thats expected
    (e.g., week25 clusters do not include week13 cells and the meta-data contains both cells)"""
    md = pd.merge(md, clust[['NAME', 'X_25', 'Y_25']], on='NAME', how='left')

    md = md.assign(sampleid=md.apply(lambda r: f'D{r["donor_id"]}_WK{r["vaccination__time_since"]}_STIM{r["Stimulated"]}', axis=1))

    cts13 = pd.read_csv(opj(bigdata_folder, 'darrah_Week13.Filtered.cells.txt'), sep='\t')
    cts25 = pd.read_csv(opj(bigdata_folder, 'darrah_Week25.Filtered.cells.txt'), sep='\t')

    """Genes (32824) x Cells (162490)"""
    cts = pd.concat((cts13, cts25), axis=1)

    out = {}
    for (sid, ctype), gby in md.groupby(['sampleid', 'cell_type__ontology_label']):
         out[(sid, ctype)] = cts.iloc[:, gby.index].sum(axis=1)
    out = pd.DataFrame(out, index=cts.index)
    out.columns = [f'{i}_{j}' for i, j in out.columns]
    out.to_csv(opj(data_folder, 'pseudo_bulk_wk13_wk25.csv'), index=True)

    """Downsample to n=downsamples cells"""
    np.random.seed(3)
    sample_factor = md.shape[0] / downsamples
    out = []
    for (sid, ctype), gby in md.groupby(['sampleid', 'cell_type__ontology_label']):
        if gby.shape[0] < 20:
            nsample = gby.shape[0]
        else:
            nsample = int(np.round(gby.shape[0] / sample_factor))
        rind = np.random.permutation(gby.shape[0])[:nsample]
        out.append(cts.loc[:, gby['NAME'].iloc[rind]])

    out = pd.concat(out, axis=1)
    out.to_csv(opj(data_folder, 'darrah_downsample_cts.csv'), index=True)

    """gby['NAME'] contains cell identifiers like 'DDF16_WK13_STIMYES' which also
    appear as columns in the cts data"""

    md_ss = md.set_index('NAME').loc[out.columns].reset_index()
    md_ss.to_csv(opj(data_folder, 'darrah_downsample_meta.csv'), index=True)
    


if __name__ == '__main__':
    make_pseudo_bulk()