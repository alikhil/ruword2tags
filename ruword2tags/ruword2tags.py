from __future__ import print_function

import gzip
import pathlib
import os
import pickle

from trie_node import TrieNode


class RuWord2Tags:
    dict_filename = 'ruword2tags.dat'

    def __init__(self):
        self.ending_len = None
        self.index2tagset = None
        self.ending2tagsets = None
        self.trie_root = None

    def load(self):
        module_folder = pathlib.Path(__file__).resolve().parent
        p = os.path.join(module_folder, '../output', self.dict_filename)
        if not os.path.exists(p):
            p = os.path.join(module_folder, self.dict_filename)

        with gzip.open(p, 'r') as f:
            data = pickle.load(f)
            self.ending_len = data['ending_len']
            self.index2tagset = data['index2tagset']
            self.ending2tagsets = data['ending2tagsets']
            self.trie_root = data['trie_root']

    def __getitem__(self, word):
        ending = word[-self.word_ending:] if len(word) > self.ending_len else u''
        if ending in self.ending2tagsets:
            for itagset in self.ending2tagsets[ending]:
                yield self.index2tagset[itagset]
        else:
            for itagset in self.trie_root.find_tagsets(word):
                yield self.index2tagset[itagset]
