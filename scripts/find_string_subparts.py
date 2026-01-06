def sort_string_list_by_length(l):
    l = sorted(l, key=len)
    return l

def is_a_subpart(parts, subpart):
    for part in parts:
        if subpart in part:
            return part
    return None

def find_string_subparts(parts):
    parts = sort_string_list_by_length(parts)
    subparts = []
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            outer_part = is_a_subpart(parts[j:], parts[i])
            if outer_part != None:
                subparts.append(parts[i])
                print(f"{parts[i]} is a subpart of {outer_part}.")
                break
    return subparts
