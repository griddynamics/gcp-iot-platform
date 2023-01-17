import datetime
import os
import torch
import pandas as pd

from argparse import ArgumentParser
from datetime import datetime
from re import match
from google.cloud.storage import Client as GSClient, Blob
from google.cloud.logging import Client as GLogClient
from torch.utils.data import DataLoader
from torch import nn

from trainer.data import TimeSeriesDataset
from trainer.models import LinearModel
from trainer.trainer import Trainer



def read_cloud_data(pattern, gsclient):
    if pattern.endswith('.csv') and '*' not in pattern:
        res = pd.read_csv(pattern)
        return res.drop_duplicates()

    splits = pattern[:pattern.find('*')].split('/')
    prefix = '/'.join(splits[3:])
    dfs = []
    blobs = gsclient.list_blobs(splits[2], prefix=prefix)
    for blob in blobs:
        if not blob.name.endswith('.csv'):
            continue
        try:
            df = pd.read_csv(f"gs://{blob.bucket.name}/{blob.name}")
            dfs.append(df)
        except pd.errors.EmptyDataError:
            # Ignoring empty files
            continue
    # concatenationg slices of data from different time ranges
    assert len(dfs) > 0, "There must be at least 1 non-empty file to get data for training"
    return pd.concat(dfs, ignore_index=True).drop_duplicates()



if __name__ == '__main__':

    parser = ArgumentParser("Anomaly Detection Cloud Trainer")
    parser.add_argument('-n','--experiment-name', dest='experiment_name', default='linear01', 
                        help='name of experiment')
    parser.add_argument('-d','--data-path', required=True, dest='data_path',
                        help='path to GCS location of data file')
    parser.add_argument('-l','--learning-rate', type=float, dest='learning_rate', default=1E-5)
    parser.add_argument('-e','--epochs', dest='epochs', type=int, default=100)
    parser.add_argument('-b','--batch-size', dest='batch_size', type=int, default=8)
    parser.add_argument('-s','--early-stopping', dest='early_stopping', type=int, default=5,
                        help='stop after this number of consequentive epochs witout improvements')
    parser.add_argument('-t','--training-part', dest='split', type=float, default=0.75,
                        help='part of data which will be used for training')
    
    args = parser.parse_args()
    args.experiment_name += datetime.now().strftime("_%Y%m%d")

    project_number = os.environ["CLOUD_ML_PROJECT_ID"]
    GLogClient(project=project_number).setup_logging()
    storage = GSClient(project=project_number)
    data = read_cloud_data(args.data_path, storage)
    data.columns = ['timestamp', 'value']
    data.set_index('timestamp', inplace=True)
    data = data['value']
    dataset24 = TimeSeriesDataset(data, 24)
    train24, test24 = dataset24.split(args.split)
    tr24_loader = DataLoader(train24, batch_size=args.batch_size, shuffle=True, drop_last=True, prefetch_factor=2)
    ts24_loader = DataLoader(test24, batch_size=args.batch_size, shuffle=False, drop_last=True, prefetch_factor=2)

    model = LinearModel(24)
    optim = torch.optim.SGD(model.parameters(), lr=args.learning_rate, momentum=0.9)
    loss = nn.HuberLoss()

    trainer = Trainer(experiment_name=args.experiment_name, model=model, optimizer=optim, loss=loss, parameters=dict(),
                    train_loader=tr24_loader, val_loader=ts24_loader)

    trainer.train(args.epochs, early_stopping=args.early_stopping)
    model_file = sorted([os.path.join(args.experiment_name, file) 
                        for file in os.listdir(args.experiment_name) 
                        if match(r'checkpoint\d+\.pt', file)])[-1]

    output_destination = os.environ.get("AIP_MODEL_DIR")
    output_bucket = output_destination.split('/')[2]
    output_folder = '/'.join(output_destination.split('/')[3:])
    bucket = storage.bucket(output_bucket)
    Blob(output_folder + 'pytorch_model.bin', bucket).upload_from_filename(model_file)
    Blob(output_folder + 'config.json', bucket).upload_from_filename(args.experiment_name + '/config.json')
