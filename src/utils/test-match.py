from array import array
from time import sleep
import difflib



if __name__ == "__main__":
    
    #res = difflib.get_close_matches('aabcc', ['aabc', 'abcc', 'aacc', 'aabbcc'])
    #print (res)
    a = "abcabccabbacccabcc"
    #a = "abaabaabbababa"
    b = "abcc"

    s = difflib.SequenceMatcher(None, a, b)
    result = []
    #while True:
    s.set_seq1 (a[0:len(b)])
    i = 0
    total = 0
    newval = ''
    while True:
        i += 1
        print ("i=", i)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            print('{:7}   a[{}:{}] --> b[{}:{}] {!r:>8} --> {!r}'.format(tag, i1, i2, j1, j2, a[i1:i2], b[j1:j2]))
            if tag == 'equal':
                total = total + i2
                newval = a[total:total+len(b)]
                print ("i2={}, total={}, val={}".format(i2, total, newval))
                s.set_seq1 (newval)
                result.append (b[j1:j2])
                
        
        if len(newval) == 0:
            break

    print (result)

def check_longest_match():
    a = "abcabccabbacccabcc"
    #a = "abaabaabbababa"
    b = "abcc"
    s = difflib.SequenceMatcher(None, a, b)

    al = 0
    ah = len (b)
    bl = 0
    bh = len(b)
    values = []
    while True:
        res = s.find_longest_match(alo=al, ahi=ah, blo=bl, bhi=bh)
        print (res)
        if res.size == 0:
            break
        val = a[res.a: res.a+res.size]
        print ("adding:", val)
        values.append (val)
        al = res.a + res.size
        ah = al + len(b) + 1
        if ah > len(a):
            break

    print (values)