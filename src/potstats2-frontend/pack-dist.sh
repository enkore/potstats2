#!/bin/sh -xue

rm -rf dist/potstats2-frontend
ng build --prod
cd dist/potstats2-frontend
git describe > frontend.version
gzip -9 --keep *.js *.css
cd ..
tar czvf potstats2-frontend.tar.gz potstats2-frontend
