#!/bin/bash
set -e
cd /work/repo
npm install
sed -i "s|.replace(/\[^a-z0-9\]/g, '-')|.replace(/[^a-z0-9]+/g, '-')|" src/index.js
npm test
