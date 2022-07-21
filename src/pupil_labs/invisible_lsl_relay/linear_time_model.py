import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Optional, Type, Union, overload

import numpy as np
import pandas as pd
from sklearn import linear_model
from typing_extensions import Self, TypedDict


class ModelParameters(TypedDict):
    intercept: float
    slope: float


@dataclass
class TimeAlignmentModels:
    _version: ClassVar[int] = 1
    cloud_to_lsl: linear_model.LinearRegression
    lsl_to_cloud: linear_model.LinearRegression

    @overload
    def to_json(self, path: Union[str, Path]) -> None:
        ...

    @overload
    def to_json(self, path: None) -> str:
        ...

    def to_json(self, path: Union[None, str, Path] = None) -> Optional[str]:
        mapping_parameters = {
            'cloud_to_lsl': {
                'intercept': self.cloud_to_lsl.intercept_,
                'slope': self.cloud_to_lsl.coef_[0],
            },
            'lsl_to_cloud': {
                'intercept': self.lsl_to_cloud.intercept_,
                'slope': self.lsl_to_cloud.coef_[0],
            },
            'info': {
                'model_type': type(self.cloud_to_lsl).__name__,
                'version': self._version,
            },
        }
        serialized = json.dumps(mapping_parameters, indent=4)
        if path is not None:
            Path(path).write_text(serialized)
        else:
            return serialized

    @classmethod
    def read_json(cls: Type[Self], path: Union[str, Path]) -> Self:
        mapping = json.loads(Path(path).read_text())
        mapping_version = mapping["info"]["version"]
        if mapping_version != cls._version:
            raise ValueError(
                f"Incompatible version {mapping_version}. Expected {cls._version}"
            )

        cloud_to_lsl = cls._model_from_parameters(mapping["cloud_to_lsl"])
        lsl_to_cloud = cls._model_from_parameters(mapping["lsl_to_cloud"])
        return cls(cloud_to_lsl, lsl_to_cloud)

    @staticmethod
    def _model_from_parameters(
        params: ModelParameters,
    ) -> linear_model.LinearRegression:
        model = linear_model.LinearRegression()
        model.intercept_ = params['intercept']
        model.coef_ = np.array(params['intercept'])
        return model


def perform_time_alignment(
    lsl_event_data: pd.DataFrame, cloud_event_data: pd.DataFrame, timestamp_label: str
) -> TimeAlignmentModels:

    cloud_event_data[timestamp_label] = cloud_event_data['timestamp [ns]'] * 1e-9

    cloud_to_lsl = _linear_time_mapper(
        cloud_event_data[[timestamp_label]], lsl_event_data[timestamp_label]
    )
    lsl_to_cloud = _linear_time_mapper(
        lsl_event_data[[timestamp_label]], cloud_event_data[timestamp_label]
    )
    return TimeAlignmentModels(cloud_to_lsl, lsl_to_cloud)


def _linear_time_mapper(x, y):
    mapper = linear_model.LinearRegression()
    mapper.fit(x, y)

    return mapper
