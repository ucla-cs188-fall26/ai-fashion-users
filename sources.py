# where each design rule comes from. every rule in the app points at one of these keys,
# so the "why" shown to students can always name its source. each entry was checked
# against the paper itself (nov 14).
SOURCES = {
    "mackinlay": ("Mackinlay 1986, expressiveness: a chart must show the data's facts and only those facts",
                  "https://courses.ischool.berkeley.edu/i247/f05/readings/Mackinlay_APT_TOG86.pdf"),
    "cleveland": ("Cleveland & McGill 1984: position on a common scale is read most accurately, then length, "
                  "then angle and area",
                  "https://vis.arc.vt.edu/%7Enpolys/projects/safas/science.pdf"),
    "zacks": ("Zacks & Tversky 1999: people read bars as discrete comparisons and lines as trends",
              "https://howieswebs.ipage.com/pdf/zackstvbarlinemc.doc.pdf"),
    "xiong": ("Xiong et al. 2021: how bars are arranged changes which comparison viewers make",
              "https://content.ieeevis.org/year/2021/paper_v-full-1376.html"),
    "kim": ("Kim et al. 2021: readers take a chart's most visually prominent feature as its takeaway "
            "(studied with line charts)",
            "https://hci.stanford.edu/publications/paper.php?id=429"),
    "kong": ("Kong et al. 2019: people recall the message in a chart's title more than the chart itself",
             "https://experts.illinois.edu/en/publications/trust-and-recall-of-information-across-varying-degrees-of-title-v/"),
    "bao": ("Bao et al. 2022: analysts value simple charts with one clear takeaway",
            "https://arxiv.org/html/2202.01335v1"),
    "weissgerber": ("Weissgerber et al. 2015: bar graphs hide the data behind continuous measures; "
                    "show individual values, especially for small samples",
                    "https://pubmed.ncbi.nlm.nih.gov/25901488/"),
    "correll": ("Correll et al. 2020: bars must start at zero or they exaggerate differences; "
                "position-based charts need not",
                "https://arxiv.org/abs/1907.02035"),
    "cumming": ("Cumming & Finch 2005; Cumming 2009: say what error bars show, and don't read overlap "
                "of two intervals as 'no difference'",
                "https://sci.utah.edu/~kpotter/Library/Papers/cumming:2005:CIRP/index.html"),
    "rougier": ("Rougier et al. 2014, Ten Simple Rules for Better Figures: identify the message, "
                "don't trust defaults, use color with purpose, avoid chartjunk, write a caption",
                "https://fdn.montana.edu/research/ord/documents/journal.pcbi.1003833.PDF"),
    "wong": ("Wong 2011: color palette distinguishable with red-green color blindness",
             "https://www.nature.com/articles/nmeth.1618"),
    "hesterberg": ("Hesterberg 2015: for small samples, t-intervals are more accurate than bootstrap "
                   "percentile intervals",
                   "https://arxiv.org/abs/1411.5279"),
    "tea": ("Tea (Jun et al. 2019): start from the hypothesis, pick a valid test, report effect size", None),
    "expert": ("Our expert interview (Dr. Stoops): know what you're comparing, one central message, stay in 2D",
               None),
    "team": ("Team heuristic: a convention we chose, to be tested in walkthroughs", None),
}


def cite(*keys: str) -> list[dict]:
    return [{"key": k, "text": SOURCES[k][0], "url": SOURCES[k][1]} for k in keys]
