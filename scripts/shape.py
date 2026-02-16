import re
import sys
from collections import defaultdict


def shape_main(input_stream=None, tty_size=100, span=15, measures_str='_length_',
               fields_str='0', shape_marker='+'):
    if input_stream is None:
        input_stream = sys.stdin

    measures = measures_str.split(',')
    fields = fields_str.split(',')
    fields = [f for f in fields if f.isnumeric()]
    fields = fields if fields else ['0']
    shape_marker_string = shape_marker * tty_size

    buckets = 0
    bucket_discriminant = 0
    J = defaultdict(int)
    MaxJ = defaultdict(int)
    MaxOccurrences = defaultdict(int)
    TotalOccurrences = defaultdict(int)
    MatchLines = defaultdict(int)
    _ = {}

    lineno = 0
    for lineno, line in enumerate(input_stream, start=1):
        bucket_discriminant = lineno % span
        if bucket_discriminant == 0:
            buckets += 1

        for f_i, field in enumerate(fields, start=1):
            for m_i, measure in enumerate(measures, start=1):
                key = (f_i, m_i)
                value = len(re.findall(measure, line)) if measure != '_length_' else len(line)
                occurrences = max(value, 0)

                if occurrences > MaxOccurrences[key]:
                    MaxOccurrences[key] = occurrences
                TotalOccurrences[key] += occurrences
                m = max(occurrences, 0)
                J[key] += m
                if m:
                    MatchLines[key] += 1

                if bucket_discriminant == 0:
                    if J[key] > MaxJ[key]:
                        MaxJ[key] = J[key]
                    _[key, lineno // span] = J[key]
                    J[key] = 0

    if not lineno:
        print("No data received")
        return

    if bucket_discriminant:
        for f_i, field in enumerate(fields, start=1):
            for m_i, measure in enumerate(measures, start=1):
                key = (f_i, m_i)
                J[key] = J[key] / bucket_discriminant * span
                if J[key] > MaxJ[key]:
                    MaxJ[key] = J[key]
                l = (lineno - J[key] + span) / span
                _[key, l] = J[key]

    AvgOccurrences = {key: TotalOccurrences[key] / lineno for key in TotalOccurrences.keys()}

    match_found = any(MaxJ.values())

    if not match_found:
        print("Data not found with given parameters")
        return

    for f_i, field in enumerate(fields, start=1):
        print(f"stats from field: {field}")

        for m_i, measure in enumerate(measures, start=1):
            key = (f_i, m_i)
            print(f'lines with "{measure}": {MatchLines[key]}')
            print(f'occurrence: {TotalOccurrences[key]}')
            print(f'average: {AvgOccurrences[key]}')
            print(f'approx var: {(MaxOccurrences[key] - AvgOccurrences[key]) ** 2}')

            ModJ = {key: 1 if MaxJ[key] <= tty_size else tty_size / MaxJ[key] for key in MaxJ.keys()}

            for i in range(1, buckets + 1):
                print(f'lineno: {i * span}')
                marker = shape_marker_string[:int(_[key, i] * ModJ[key])]
                print(f'distribution of "{measure}": {marker}')


if __name__ == "__main__":
    shape_main()
