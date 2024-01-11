import re

def main():
    curly = 1
    innerBrace = 1
    entityCounter = 1
    Entities = {}
    comment = False
    escaped = False
    prevChar = ''
    activeBrace = ''
    activeInnerBrace = {}
    innerCurly = 0
    quote = False
    squote = False
    dquote = False

    with open('file', 'r') as f:
        for line in f:
            if not comment:
                for char in line:
                    if comment:
                        continue

                    if openCurly(char, quote, escaped):
                        if curly == 2:
                            innerCurly += 1
                        else:
                            curly += 1
                        activeBrace = char
                    elif innerOpenBrace(char, quote, escaped, squote, dquote) and not braceMatch(char, activeInnerBrace.get(innerBrace, '')):
                        innerBrace += 1
                        activeInnerBrace[innerBrace] = char
                    elif innerBrace > 1 and innerCloseBrace(char, quote, escaped, squote, dquote) and braceMatch(char, activeInnerBrace.get(innerBrace, '')):
                        del activeInnerBrace[innerBrace]
                        innerBrace -= 1
                    elif innerBrace == 1 and not innerCurly and not quote and char == '#':
                        comment = True

                    if not comment:
                        Entities[(entityCounter, curly)] = Entities.get((entityCounter, curly), '') + char
                        if curly == 2 and closeCurly(char, quote, escaped) and braceMatch(char, activeBrace):
                            if innerCurly:
                                innerCurly -= 1
                            else:
                                curly -= 1
                                activeBrace = ''
                                entityCounter += 1
                    prevChar = char
                    escaped = (char == '\\')
                    quote = (squote or dquote)

    for i in range(1, entityCounter + 1):
        for j in range(1, 3):
            if Entities.get((i, j), ''):
                print(Entities[(i, j)])

def braceMatch(char, brace):
    if brace == '{' and char == '}':
        return True
    elif brace == '[' and char == ']':
        return True
    elif brace == '(' and char == ')':
        return True
    elif brace == '"' and char == '"':
        return True
    elif brace == '\'' and char == '\'':
        return True
    else:
        return False

def openCurly(char, quote, escaped):
    if not quote and not escaped and char == '{':
        return True
    else:
        return False

def closeCurly(char, quote, escaped):
    if not quote and not escaped and char == '}':
        return True
    else:
        return False

def innerOpenBrace(char, quote, escaped, squote, dquote):
    if (char in ['[', '(']) and not quote:
        return True
    elif not escaped and char == '"' and not squote:
        dquote = True
        return True
    elif not escaped and char == '\'' and not dquote:
        squote = True
        return True
    else:
        return False

def innerCloseBrace(char, quote, escaped, squote, dquote):
    if (char in [']', ')']) and not quote:
        return True
    elif not escaped and dquote and char == '"' and not squote:
        dquote = False
        return True
    elif not escaped and squote and char == '\'' and not dquote:
        squote = False
        return True
    else:
        return False

if __name__ == "__main__":
    main()
