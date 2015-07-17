import pykeyvi

query = ""

d=pykeyvi.Dictionary("prefix-completion.keyvi")
c=pykeyvi.PrefixCompletion(d)

def get_lookup_key(query):
    return query

while query!="exit":
    query = raw_input("Query:")
    for m in c.GetFuzzyCompletions(get_lookup_key(query.strip()), 3):
        print "{} {}".format(m.GetMatchedString(), m.GetAttribute("weight"))
