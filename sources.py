# where each design rule comes from. every rule in the app points at one of these keys,
# so the "why" shown to students can always name its source.
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
    "kim": ("Kim et al. 2021: readers take a chart's most visually prominent feature as its takeaway",
            "https://hci.stanford.edu/publications/paper.php?id=429"),
    "kong": ("Kong et al. 2019: people recall the message in a chart's title more than the chart itself",
             "https://experts.illinois.edu/en/publications/trust-and-recall-of-information-across-varying-degrees-of-title-v/"),
    "bao": ("Bao et al. 2022: analysts value simple charts with one clear takeaway",
            "https://arxiv.org/html/2202.01335v1"),
    "tea": ("Tea (Jun et al. 2019): start from the hypothesis; fall back to bootstrapping; report effect size",
            None),
    "expert": ("Our expert interview (Dr. Stoops): know what you're comparing, one central message, stay in 2D",
               None),
    "team": ("Team heuristic: a convention we chose, to be tested in walkthroughs", None),
}


def cite(*keys: str) -> list[dict]:
    return [{"key": k, "text": SOURCES[k][0], "url": SOURCES[k][1]} for k in keys]
