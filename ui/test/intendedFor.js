#!/usr/bin/node

const lib = require('../src/lib');

// const $root = require('./test.root.json');
const $root = require('./openscience.json');

lib.fmapQA($root); // fmap sanity check
lib.setIntendedFor($root); // set fmap IntendedFor fields

