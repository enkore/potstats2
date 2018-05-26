#!/bin/sh -xue

rm -r dist/potstats2-frontend
ng build --prod
cd dist/potstats2-frontend
gzip -9 --keep *.js *.css
cd ..
tar czvf potstats2-frontend.tar.gz potstats2-frontend
