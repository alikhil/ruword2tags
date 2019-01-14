class TrieNode:
    def __init__(self, char):
        self.char = char
        self.hit_count = 0
        self.tagset_indeces = []
        self.nextchar2node = dict()

    def add(self, next_chars, tagset_index):
        self.hit_count += 1
        if len(next_chars) == 0:
            self.tagset_indeces.append(tagset_index)
        else:
            next_char = next_chars[0]
            if next_char not in self.nextchar2node:
                self.nextchar2node[next_char] = TrieNode(next_char)

            self.nextchar2node[next_char].add(next_chars[1:], tagset_index)

    def count_children(self):
        return 1 + sum(child.count_children() for child in self.nextchar2node.values())

    def count_leaves(self):
        return len(self.tagset_indeces) + sum(child.count_leaves() for child in self.nextchar2node.values())

    def find_tagsets(self, word):
        if word:
            next_char = word[0]
            if next_char in self.nextchar2node:
                for itagset in self.nextchar2node[next_char].find_tagsets(word[1:]):
                    yield itagset
        else:
            for itagset in self.tagset_indeces:
                yield itagset

