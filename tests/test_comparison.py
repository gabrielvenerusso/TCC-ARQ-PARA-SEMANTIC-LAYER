import unittest
from mvp.__main__ import compare,normalize_sparql,normalize

class ComparisonTests(unittest.TestCase):
    def test_duplicate_loss_fails(self):
        self.assertFalse(compare({'fields':['p'],'rows':[['2'],['2']]},
                                 {'fields':['p'],'rows':[['2']]})['correct'])
    def test_optional_is_not_empty_or_zero(self):
        self.assertIsNone(normalize(None,'string?'))
        self.assertFalse(compare({'fields':['c'],'rows':[[None]]},
                                 {'fields':['c'],'rows':[['']]})['correct'])
    def test_decimal_no_binary_float_rounding(self):
        self.assertEqual(normalize('9007199254740993.10','decimal'),'9007199254740993.1')
    def test_reject_wrong_literal_type(self):
        q={'kind':'select','fields':{'n':'integer'}}
        r={'head':{'vars':['n']},'results':{'bindings':[{'n':{'type':'literal','value':'2','datatype':'http://www.w3.org/2001/XMLSchema#string'}}]}}
        with self.assertRaises(ValueError):normalize_sparql(r,q)
    def test_bag_ignores_order_and_ordered_comparison_does_not(self):
        a={'fields':['n'],'rows':[['1'],['2']]};b={'fields':['n'],'rows':[['2'],['1']]}
        self.assertTrue(compare(a,b)['correct']);self.assertFalse(compare(a,b,True)['correct'])
    def test_unbound_required_rejected(self):
        with self.assertRaises(ValueError):normalize(None,'integer')
    def test_ask_rejects_string_false(self):
        with self.assertRaises(ValueError):normalize_sparql({'boolean':'false'},{'kind':'ask'})

if __name__=='__main__':unittest.main()
