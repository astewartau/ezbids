#!/usr/bin/node

const lib = require('../src/lib');

// const $root = require('./test.root.json');
const $root = require('./Video_root.json');

lib.funcQA($root);
lib.fmapQA($root); // fmap sanity check
lib.setRun($root);
lib.updateErrors($root);
lib.setIntendedFor($root); // set fmap IntendedFor fields

