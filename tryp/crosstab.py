import imp
import pandas as pd
import numpy as np

from common import roundrobin
from excel import to_excel as to_excel


class Crosstab(object):
    def __init__(self, metadata):
        self.xcoord, self.ycoord, self.zcoord = [], [], []
        self.xaxis = metadata.xaxis
        self.yaxis = metadata.yaxis
        self.zaxis = metadata.zaxis
        self.visible_xaxis_summary = metadata.visible_xaxis_summary
        self.visible_yaxis_summary = metadata.visible_yaxis_summary
        self.excel = metadata.excel
        self.dataframe = self._crosstab(metadata.source_dataframe,
                                        self.xaxis,
                                        self.yaxis,
                                        self.zaxis)
        self._extend(metadata.extmodule)

    def to_excel(self):
        to_excel(self)

    def _extend(self, extmodule):
        if extmodule:
            extmodule = imp.load_source(extmodule[0], extmodule[1])
            extmodule.extend(self)
        self.values_labels = self._values_labels(self.dataframe)

    def _crosstab(self, source_dataframe, xaxis, yaxis, zaxis):
        df = source_dataframe.groupby(xaxis + yaxis).sum()
        df = df[zaxis].unstack(xaxis)
        if xaxis:
            df = self._xaxis_summary(source_dataframe,
                                     xaxis,
                                     yaxis,
                                     zaxis,
                                     df)
        return self._yaxis_summary(yaxis, df)

    def _values_labels(self, ct):
        if isinstance(ct.columns, pd.MultiIndex):
            return map(lambda x: x[-1], ct.columns)
        return ct.columns

    def _xaxis_summary(self, source_dataframe, xaxis, yaxis, zaxis, ctdf):
        for idx in ctdf.columns:
            self.xcoord.append(self.xaxis[-1])

        ## CREATE SUBTOTALS FOR EACH COLUMNS
        for i in range(0, len(self.visible_xaxis_summary)):
            subtotal = source_dataframe.groupby(xaxis[:i+1] + yaxis).sum()[zaxis]
            subtotal = subtotal[zaxis].unstack(xaxis[:i+1])
        
            for col in subtotal.columns:
                scolumns = col + (col[-1],) * (len(xaxis) - len(col) + 1)
                ctdf[scolumns] = subtotal[col]
                self.xcoord.append(self.visible_xaxis_summary[i])
        ## END

        ## CREATE COLUMNS GRAND TOTAL
        for value in zaxis:
            total = source_dataframe.groupby(yaxis + xaxis[-1:]).sum()[value]
            keys = tuple([''] * len(xaxis))
            ctdf[(value,) + keys] = total.unstack(xaxis[-1:]).sum(axis=1)
            self.xcoord.append('')
        ## END

        ## REORDER AXIS 1 SO THAT AGGREGATES ARE THE LAST LEVEL
        order = range(1, len(xaxis) + 1) + [0]
        ct = ctdf.reorder_levels(order, axis=1)
        ## END

        print self.zaxis
        sorted_columns = self._sort_axis(ct.columns, self.visible_xaxis_summary, self.xcoord)
        sorted_columns = map(lambda x: x[0][:-1] + (x[1],) , zip(sorted_columns, self.zaxis * (len(sorted_columns) / len(self.zaxis))))

        return ct.reindex_axis(axis=1, labels=sorted_columns)

    def _yaxis_summary(self, yaxis, df):
        for idx in df.index:
            self.ycoord.append(self.yaxis[-1])

        ## CREATE SUBTOTALS FOR EACH INDEX
        subtotals = []
        for i in range(len(self.visible_yaxis_summary)):
            for idx in set([x[:i+1] for x in df.index]):
                sindex = idx + (idx[-1],) * (len(yaxis) - len(idx))
                stotal = pd.DataFrame({sindex: df.ix[idx].sum()}).T
                subtotals.append(stotal)
                self.ycoord.append(self.visible_yaxis_summary[i])
        ## END

        ## CREATE INDEX GRAND TOTAL
        gindex = tuple([''] * len(yaxis))
        gtotal = pd.DataFrame({gindex: df.ix[:].sum()}).T
        subtotals.append(gtotal)
        self.ycoord.append('')
        ## END

        df = pd.concat([df] + subtotals)
        return df.reindex_axis(axis=0, labels=self._sort_axis(df.index, self.visible_yaxis_summary, self.ycoord))

    def _sort_axis(self, axis, visible_axis, coord):
        sorter = []
        for i, idx in enumerate(axis):
            if coord[i] in visible_axis:
                nans = [np.NaN,] * (visible_axis.index(coord[i])+ 1)
                nans[visible_axis.index(coord[i])] = 1
                sorter.append([x for x in roundrobin(idx, nans)])
            else:
                nans = (np.NaN,) * len(visible_axis)
                sorter.append([x for x in roundrobin(idx, nans)])

        lexsort = np.lexsort([x for x in reversed(zip(*sorter))])
        sorted_index = []
        for lx in lexsort:
            idx = zip(*axis)
            lex = tuple([idx[x][lx] for x in range(len(idx))])
            sorted_index.append(lex)
        return sorted_index
