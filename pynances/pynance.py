# Import all libraries needed for the tutorial

# General syntax to import specific functions in a library: 
##from (library) import (specific library function)
from pandas import DataFrame, read_csv

import numpy as np
# General syntax to import a library but no functions: 
##import (library) as (give the library a nickname/alias)
import matplotlib.pyplot as plt
import pandas as pd #this is how I usually import pandas
import sys #only needed to determine Python version number
import matplotlib #only needed to determine Matplotlib version number
import time
import functools
import operator
import re
import locale
import calendar
import collections
import datetime
from IPython.display import display
import plotly
from plotly.graph_objs import Bar, Layout

pd.options.display.float_format = '{:,.2f}'.format

import pandas as pd
from pandas import DataFrame, read_csv
from datetime import datetime

import numpy as np

#local imports
from pynances.DKB import DKB

class Pynance():
    class ColumnNaming():
        def __init__(self):
            language = locale.getdefaultlocale()
            self._date = 'date'
            self._client = 'client'
            self._value = 'value'
            self._type = 'typ'
            self._info = 'info'
            self._account = 'account'
            if language[0] == 'de_DE':
                self._unknownType = 'Undefiniert'
            else:
                self._unknownType = 'undefined'
    
    def __init__(self):
        self.df = None;
        self.accountNumbers = []
        self.currentMoney = {}
        self.columnNaming = self.ColumnNaming()
        pass
    
    def setGroups(self, groupDict):
        self.groupDict = groupDict
        self.renameSimilars(self.columnNaming._client, self.columnNaming._type)

        
    def renameSimilars(self, renameField, groupField):
        # renaming similar stuff
        for key, values in self.groupDict.items():
            for val in values:
                self.df[renameField]= self.df[renameField].str.replace(val+".*", val, case=False)

        for key, values in self.groupDict.items():
            group_filter = self.df[renameField].str.contains('|'.join(map(re.escape, values)), flags=re.IGNORECASE)==True
            self.df.ix[group_filter, groupField] = key

    
    def getCurrentMoney(self, filepath, bank):
        locale.setlocale( locale.LC_ALL, 'German' ) 
        currentMoney = 0
        with open(filepath, 'rt') as f:
            rows = list(csv.reader(f,delimiter=';'))
            if bank == "DKB":
                moneyStr = rows[4][1]
                if moneyStr.find(',') > 0:
                    currentMoney = moneyStr.replace('.', '').replace(',','.')
                elif moneyStr.find('EUR'):
                    currentMoney = moneyStr[:moneyStr.find('EUR')]
            elif bank == "VR":
                currentMoney = rows[-1][-2].replace('.', '').replace(',','.')
                
        #print(currentMoney)
        return currentMoney

    
    def getColumns(self,filter):
        return self.df.filter(items=filter)

    def setColumns(self,filter):
        self.df = self.df.filter(items=filter)
    
    def readCSV(self, filename, banktype):
        if banktype == 'DKB_giro':
            (accountNumber, currentMoney, df) = DKB().readCSV_giro(filename, self.columnNaming)
        elif banktype == 'DKB_visa':
            (accountNumber, currentMoney, df) = DKB().readCSV_visa(filename, self.columnNaming)
        elif banktype == 'VR_giro':
            (accountNumber, currentMoney, df) = VR().readCSV_giro(filename, self.columnNaming)
            
        self.accountNumbers.append(accountNumber)
        
        if df.empty:
            return
        
        self.currentMoney[accountNumber] = currentMoney

        if isinstance(self.df, pd.DataFrame):
            self.df = self.df.append(df)
        else:
            self.df = df;
        
        #print(df.columns)
        #if 'Kontonummer' in self.df.columns:
        #    self.df.ix[self.df.Kontonummer.str.contains('|'.join(self.accountNumbers), flags=re.IGNORECASE)==True, 'Typ'] = 'Verschiebungen'
        self.df.sort_index(ascending=1, inplace=True)
        
    
        
        
    def createMonthlySums(self, columnDict, filterPosValues=False, filterNegValues=False, negateValues=False):
        columnValue = self.columnNaming._value
        columnType = self.columnNaming._type
        columnInfo = self.columnNaming._info
        columnClient = self.columnNaming._client

        monthly = pd.DataFrame();
                
        for key, value in columnDict.items():
            if type(value) is list:
                for v in value:
                    part = self.df[self.df[columnType] == v]
                    monthly = monthly.append(part)
            else:
                part = self.df[self.df[columnType] == key]
                monthly = monthly.append(part)
        
        # set unknown types
        monthly = monthly.append(self.df[self.df[columnType] == self.columnNaming._unknownType])
        
        if filterPosValues:
            monthly = monthly.ix[monthly[columnValue] <= 0]
        if filterNegValues:
            monthly = monthly.ix[monthly[columnValue] > 0]
        if negateValues:
            monthly[columnValue] = monthly[columnValue]*-1;
            
        monthly.index = monthly.index.to_period('M')
        monthly = monthly.loc[:,[columnType, columnValue, columnClient]]
        monthly[columnInfo] = monthly[columnValue].apply(str) + ', ' + monthly[columnClient].apply(str) # concat money, info
        monthly[columnInfo] = monthly[columnInfo].str[:30] # shorten it to 30 chars
        aggFunc = { columnValue: { columnValue : lambda x: np.sum(x)}, columnInfo: { columnInfo : lambda x: '<br>'.join(x)}}
        monthlyTypes = monthly.groupby([monthly.index,columnType]).agg(aggFunc)
        monthlyTypes.columns = monthlyTypes.columns.droplevel(0)
        ausgaben = monthlyTypes
        return ausgaben
        
    def plotCurrentMoney(self):
        dictlist = []
        for key, value in self.currentMoney.items():
            temp = [key,value]
            dictlist.append(temp)
    
        #print(dictlist)
        zippedList = list(map(list, zip(*dictlist)))
        plotly.offline.iplot({
            "data": [{
                "values": zippedList[1],
                "labels": zippedList[0],
                "type": "pie"
                    }]
        })
        
    def plotMonthlyStackedBar(self, columnDict, plotTitle, filterPosValues=False, filterNegValues=False, negateValues=False, showUnknownTypes=True):
        columnValue = self.columnNaming._value
        columnInfo = self.columnNaming._info

        ausgaben = self.createMonthlySums(columnDict, filterPosValues, filterNegValues, negateValues)
        
        # detailed info about payments 
        ausgabenInfo = ausgaben.unstack(1)[columnInfo]
        ausgabenInfo.reset_index(inplace=True)

        # rough values and month dates
        ausgabenValue = ausgaben.unstack(1)[columnValue].abs()
        ausgabenValue.reset_index(inplace=True)
        #print(ausgabenValue.head())
        if 'index' in ausgabenValue.columns:
            ausgabenValue = ausgabenValue.set_index('index')
        
        plotColumnsList = []
        for key, value in columnDict.items():
            if type(value) is list:
                for v in value:
                    if (v not in plotColumnsList):
                        plotColumnsList.append(v)
            elif (value not in plotColumnsList):
                plotColumnsList.append(value)
                
        if showUnknownTypes:
            plotColumnsList.append(self.columnNaming._unknownType)
                
        data = []
        for column in plotColumnsList:
            if column == "index" or column not in ausgabenValue.columns:
                continue
            data.append(
                Bar(
                    x=ausgabenValue.index.map(str),
                    y=ausgabenValue[column],
                    text=ausgabenInfo[column],
                    name=column,
                    hoverlabel=dict( font=dict(color='white', size=8))
                ),
            )

        # IPython notebook
        plotly.offline.iplot({
        "data": data,
        "layout": Layout(
                barmode='stack',
                title=plotTitle,
                autosize=True,
            )
        })