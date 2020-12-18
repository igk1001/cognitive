import difflib

# accepts a pattern and sequence as arrays of characters [abcd] 
def get_matching_sequences(pattern, match):   
    a = match
    b = pattern

    print ('pattern={}, match={}'.format(pattern, match))
    s = difflib.SequenceMatcher(None, a, b)
    results = []
    s.set_seq1 (a[0:len(b)])
    total = 0
    newval = ''
    while True:
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            print('{:7}   a[{}:{}] --> b[{}:{}] {!r:>8} --> {!r}'.format(tag, i1, i2, j1, j2, a[i1:i2], b[j1:j2]))
            if tag == 'equal':
                total = total + i2
                newval = a[total:total+len(b)]
                print ("i2={}, total={}, val={}".format(i2, total, newval))
                s.set_seq1 (newval)
                results.append (b[j1:j2])
                
        
        if len(newval) == 0:
            break

    return results