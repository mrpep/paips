#!/bin/bash
set -x

for n in 100 200 300 400 500; do
paiprun configs/ex3.yaml --output_path "my_experiments/rf_regressor_$ntrees" --mods "global/n_estimators=$n";
done