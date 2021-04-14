#!/bin/bash
set -x

for test in ex1 ex2 ex3 ex4 ex5 ex6; do
paiprun configs/$test.yaml --no-caching;
paiprun configs/$test.yaml;  
done