import sys
from utils.analytics import get_matching_sequences

def test_match():
    a = "abcabccabbacccabcc"
    b = "abcc"
    res = get_matching_sequences(b,a)
    print (res)
    expected = ['abc', 'abcc', 'ab', 'b', 'cc', 'abcc']
    assert res == expected
    