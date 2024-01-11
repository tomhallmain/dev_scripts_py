import re
from collections import Counter

class TextEntities:
    def __init__(self, min_count=0, separator=r'\s+'):
        self.min_count = min_count
        self.separator = separator
        self.counter = Counter()

    def process_file(self, file_path):
        with open(file_path, 'r') as file:
            for line in file:
                self.counter.update(re.split(self.separator, line.strip()))

    def print_entities(self):
        for entity, count in self.counter.items():
            if count > self.min_count:
                print(count, entity)

# Usage:
# text_entities = TextEntities(min_count=0, separator=r'\s+')
# text_entities.process_file('file_path')
# text_entities.print_entities()
