# -*- coding: utf-8 -*-
from __future__ import print_function

import gzip
import pathlib
import os
import pickle
import io
import argparse
#import dill
from collections import namedtuple


#TrieNode = namedtuple('TrieNode', 'char tagset_indeces nextchar2node')


def create_trie_node(char):
    return char, [], dict()


def add_to_trie_node(node, next_chars, tagset_index):
    if len(next_chars) == 0:
        node[1].append(tagset_index)
    else:
        next_char = next_chars[0]
        if next_char not in node[2]:
            node[2][next_char] = create_trie_node(next_char)

        add_to_trie_node(node[2][next_char], next_chars[1:], tagset_index)


def find_tagsets_in_trie_node(node, word):
    if word:
        found_tagsets = []
        next_char = word[0]
        if next_char in node[2]:
            found_tagsets.extend(find_tagsets_in_trie_node(node[2][next_char], word[1:]))
        return found_tagsets
    else:
        return node[1]


class RuWord2Tags:
    dict_filename = 'ruword2tags.dat'

    def __init__(self):
        self.ending_len = None
        self.index2tagset = None
        self.ending2tagsets = None
        self.trie_root = None
        self.all_ending2tagsets = None

    def load(self, dict_path=None):
        if dict_path is None:
            module_folder = str(pathlib.Path(__file__).resolve().parent)
            p = os.path.join(module_folder, '../output', self.dict_filename)
            if not os.path.exists(p):
                p = os.path.join(module_folder, self.dict_filename)
        else:
            p = dict_path

        with gzip.open(p, 'r') as f:
            data = pickle.load(f)
            self.ending_lens = data['ending_lens']
            self.index2tagset = data['index2tagset']
            self.ending2tagsets = data['ending2tagsets']
            self.all_ending2tagsets = data['all_ending2tagsets']
            self.trie_root = data['trie_root']

    def __getitem__(self, word):
        hit = False
        for ending_len in self.ending_lens:
            ending = word[-ending_len:] if len(word) > ending_len else u''
            if ending in self.ending2tagsets:
                for itagset in self.ending2tagsets[ending]:
                    yield self.index2tagset[itagset]
                hit = True
                break

        if not hit:
            for itagset in find_tagsets_in_trie_node(self.trie_root, word):
                hit = True
                yield self.index2tagset[itagset]

        if not hit:
            for ending_len in reversed(self.ending_lens):
                ending = word[-ending_len:] if len(word) > ending_len else u''
                if ending in self.all_ending2tagsets:
                    for itagset in self.all_ending2tagsets[ending]:
                        yield self.index2tagset[itagset]
                    hit = True
                    break


def run_tests(dict_path=None):
    print('Start testing...')
    word2tags = RuWord2Tags()
    word2tags.load(dict_path)

    cases = [(u'а', [u'СОЮЗ', u'ЧАСТИЦА']),
             (u'кошки', [u'СУЩЕСТВИТЕЛЬНОЕ ПАДЕЖ=ИМ РОД=ЖЕН ЧИСЛО=МН',
                         u'СУЩЕСТВИТЕЛЬНОЕ ПАДЕЖ=РОД РОД=ЖЕН ЧИСЛО=ЕД']),
             (u'на', [u'ГЛАГОЛ ВИД=НЕСОВЕРШ ЛИЦО=2 НАКЛОНЕНИЕ=ПОБУД ТИП_ГЛАГОЛА=СТАТИЧ ЧИСЛО=ЕД',
                      u'ПРЕДЛОГ ПАДЕЖ=ВИН ПАДЕЖ=МЕСТ ПАДЕЖ=ПРЕДЛ',
                      u'ЧАСТИЦА'])]

    for word, required_tagsets in cases:
        model_tagsets = list(word2tags[word])
        if len(model_tagsets) != len(required_tagsets):
            #for tagset in model_tagsets:
            #    print(u'DEBUG@112 word={} tagset={}'.format(word, tagset))
            raise AssertionError(u'word="{}": {} tagset(s) required, {} found'.format(word, len(required_tagsets), len(model_tagsets)))

        for model_tagset in model_tagsets:
            if model_tagset not in required_tagsets:
                raise AssertionError(u'Tagset "{}" for word "{}" is not valid'.format(model_tagset, word))

    print('All tests PASSED.')


def normalize_word(s):
    if len(s) > 2 and s[0] == "'" and s[-1] == "'":
        s = s[1:-1]

    return s.replace(' - ', '-').replace('ё', 'е').strip().lower()


ignore_tags = set('ОДУШ:ОДУШ ОДУШ:НЕОДУШ ПАДЕЖВАЛ:РОД МОДАЛЬНЫЙ:0 ПЕРЕЧИСЛИМОСТЬ:ДА ПЕРЕХОДНОСТЬ:ПЕРЕХОДНЫЙ ПЕРЕХОДНОСТЬ:НЕПЕРЕХОДНЫЙ ПАДЕЖВАЛ:ТВОР ПАДЕЖВАЛ:ИМ ПАДЕЖВАЛ:ДАТ ПАДЕЖВАЛ:ВИН СГД_ВРЕМЯ:Начать ВОЗВРАТНОСТЬ:0 ВОЗВРАТНОСТЬ:1'.split())


def clean_tagset(tagset):
    return ' '.join(t for t in tagset.split() if t not in ignore_tags).replace(':', '=')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Сборка грамматического словаря')
    parser.add_argument('--src', type=str, default='../data/word2tags.dat', help='Source grammatical dictionary file path')
    parser.add_argument('--output', type=str, default='../output/ruword2tags.dat', help='Result dictionary file path')
    parser.add_argument('--words', type=str, help='List of known words (all dictionary words are included by default)')

    args = parser.parse_args()
    knownwords_file = args.words
    word2tags_path = args.src
    output_file = args.output

    # Строим словарь из исходных данных

    known_words = None
    if knownwords_file is not None:
        # Загружаем из указанного файла список слов, которые попадут в итоговую модель.
        print('Загружаем список слов для сборки кастомного словаря из {}'.format(knownwords_file))
        known_words = set()
        with io.open(knownwords_file, 'r', encoding='utf-8') as rdr:
            for line in rdr:
                word = line.replace(chr(65279), '').strip()
                known_words.add(word.lower())
        print('Загружено {} слов из {}'.format(len(known_words), knownwords_file))

    word2tagsets = dict()
    tagset2index = dict()
    nb_words = 0
    print('Loading dictionary from {}'.format(word2tags_path))
    with io.open(word2tags_path, 'r', encoding='utf-8') as rdr:
        for line in rdr:
            tx = line.replace(chr(65279), '').strip().split('\t')
            if len(tx) >= 3:
                word = normalize_word(tx[0])
                if known_words is None or word in known_words:
                    pos = tx[1]
                    lemma = normalize_word(tx[2])
                    tags = clean_tagset(tx[3]) if len(tx) == 4 else u''

                    tagset = (pos + ' ' + tags).strip()

                    if tagset not in tagset2index:
                        tagset2index[tagset] = len(tagset2index)

                    itagset = tagset2index[tagset]

                    if word not in word2tagsets:
                        word2tagsets[word] = [itagset]
                    else:
                        word2tagsets[word].append(itagset)

                    nb_words += 1

    print('Number of wordentries={}'.format(nb_words))
    print('Number of tagsets={}'.format(len(tagset2index)))

    for word in u'а и у с к'.split():
        assert(word in word2tagsets)

    ending_lens = [3, 4, 5]
    processed_words = set()
    ending2tagsets = dict()
    all_ending2tagsets = dict()

    for ending_len in ending_lens:
        print('Start processing ending_len={}'.format(ending_len))
        e2tagsets = dict()
        for word, tagsets in word2tagsets.items():
            if word not in processed_words and len(word) > ending_len:
                ending = word[-ending_len:]
                if ending not in e2tagsets:
                    e2tagsets[ending] = set(tagsets)
                else:
                    e2tagsets[ending].update(tagsets)

        all_ending2tagsets.update(e2tagsets)
        print('Number of distinct endings={}'.format(len(e2tagsets)))

        # Уберем окончания, которые дают списки тегов хотя бы с 1 ошибкой
        bad_endings = set()
        for word, word_tagsets in word2tagsets.items():
            if word not in processed_words and len(word) > ending_len:
                ending = word[-ending_len:]
                ending_tagsets = e2tagsets[ending]
                if set(word_tagsets) != ending_tagsets:
                    bad_endings.add(ending)

        print('Number of bad endings={}'.format(len(bad_endings)))

        e2tagsets = dict(filter(lambda z: z[0] not in bad_endings, e2tagsets.items()))

        # Теперь пометим слова, которые подходят под оставшиеся хорошие окончания.
        nb_matched_words = 0
        for word in word2tagsets.keys():
            if len(word) > ending_len:
                ending = word[-ending_len:]
                if ending in e2tagsets:
                    processed_words.add(word)
                    nb_matched_words += 1

        print('nb_matched_words={}'.format(nb_matched_words))

        # Переносим оставшиеся хорошие окончания в основной список
        ending2tagsets.update(e2tagsets)

    print('Number of good endings={}'.format(len(ending2tagsets)))
    print('Number of all endings={}'.format(len(all_ending2tagsets)))

    print('Building TRIE...')
    trie_words = []
    for word, word_tagsets in word2tagsets.items():
        if word not in processed_words:
            # Слово не было обработано окончаниями.
            for itagset in word_tagsets:
                trie_words.append((word, itagset))

    trie_root = create_trie_node('')
    for word, itagset in trie_words:
        add_to_trie_node(trie_root, word, itagset)

    print('Number of words in TRIE={}'.format(len(trie_words)))

    index2tagset = dict((i, t) for (t, i) in tagset2index.items())

    lexicon_data = {'ending_lens': ending_lens,
                    'index2tagset': index2tagset,
                    'ending2tagsets': ending2tagsets,
                    'all_ending2tagsets': all_ending2tagsets,
                    'trie_root': trie_root}

    with gzip.open(output_file, 'w') as f:
        pickle.dump(lexicon_data, f, protocol=2)

    print('Сохранен файл словаря размером {:d} Мб'.format(int(os.path.getsize(output_file)/1000000)))

    # Теперь запускаем проверки для построенного словаря
    run_tests(output_file)

    word2tags = RuWord2Tags()
    word2tags.load(output_file)

    for word in u'кошки ккошки на'.split():
        for i, tagset in enumerate(word2tags[word]):
            print(u'{}[{}] => {}'.format(word, i, tagset))
