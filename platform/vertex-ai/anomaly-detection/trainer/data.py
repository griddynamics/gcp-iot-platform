import numpy as np
import pandas as pd
import datetime
from torch.utils.data import Dataset
from typing import Tuple, Union, Optional
from copy import deepcopy


class TimeSeriesDataset(Dataset):
    def __init__(self, series: pd.Series, points_before: int, difference: bool = False, include_date_features:bool = False, part: Optional[str]=None, recurrent:bool = False):
        super().__init__()
        self.points_before = points_before # MA
        self.difference = difference  # Integrated
        self.recurrent = recurrent
        self.part = part
        self.ts = series.copy()
        self.ts.index = pd.to_datetime(self.ts.index)
        self.preprocess_data()
        
        self.rows = np.array([self.ts.iloc[i-points_before:i] for i in range(points_before, len(self.ts))])
        self.labels = [self.ts.iloc[i] for i in range(points_before, len(self.ts))]
        
        self.include_date_features = include_date_features
        if include_date_features:
            self._add_date_features()
    
    def preprocess_data(self) -> None:
        self.ts.sort_index(inplace=True)
        if self.difference:
            self._first = self.ts.iloc[0]
            self._last = self.ts.iloc[-1]
            self.ts = self.ts.diff().dropna()
        self.period = (self.ts.index[-1] - self.ts.index[-2]).seconds
        # Normalizing
        self._mean = self.ts.mean()
        self._std = self.ts.std()
        self.ts = (self.ts - self._mean) / self._std
        
    def _add_date_features(self) -> None:
        # Calculate date features
        # Join existing features with date features
        #TODO
        pass
        
    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> Tuple[np.ndarray, float]:
        if self.recurrent:
            #TODO Check how it works with recurrent layers
            return [self.rows[idx]], self.labels[idx]
        else:
            return self.rows[idx], self.labels[idx]
    
    def split(self, train_part: Union[int, float, datetime.datetime] = .7, test_part: Union[None, int, float, datetime.datetime] = None):
        if type(train_part) is int:
            points = train_part
        elif type(train_part) is float:
            points = int(self.__len__() * train_part)
        elif type(train_part) is datetime.datetime:
            points = sum(self.ts.index < pd.to_datetime(train_part.astimezone(datetime.timezone.utc)))

        train = deepcopy(self)
        train.rows = train.rows[:points]
        train.labels = train.labels[:points]
        train.ts = train.ts[:points + self.points_before]
        train.part = 'train'
        test = deepcopy(self)
        test.rows = test.rows[points:]
        test.labels = test.labels[points:]
        test.ts = test.ts[points:]
        test.part = 'test'
        return train, test
    
    def denormalize(self, x):
        return x * self._std + self._mean
    
    def __str__(self):
        return super().__str__() + f'\nPoints before: {self.points_before},{" Difference," if self.difference else ""}'+\
                                   f'{" with date features," if self.include_date_features else ""}'+\
                                   f'\n Total rows: {self.__len__()} (from {min(self.ts.index)} to {max(self.ts.index)})'
