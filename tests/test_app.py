from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / 'app.py'


def test_comparison_workflow_revises_chart_and_keeps_choices():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox[0].select('grades_by_major.csv').run()
    app.radio(key='stage').set_value('2 · Your question').run()
    app.radio(key='goal').set_value('comparison')
    app.multiselect[0].set_value(['major', 'gpa']).run()
    assert not app.exception
    assert any(h.value == 'Bar chart' for h in app.subheader)
    app.radio(key='intent_grades_by_major.csv').set_value('variation').run()
    assert any(h.value == 'Box plot' for h in app.subheader)
    app.radio(key='stage').set_value('3 · Your figure').run()
    app.radio(key='stage').set_value('2 · Your question').run()
    assert app.multiselect[0].value == ['major', 'gpa']
    assert app.radio(key='intent_grades_by_major.csv').value == 'variation'
    app.radio(key='intent_grades_by_major.csv').set_value('individual').run()
    assert any(h.value == 'Strip (dot) plot' for h in app.subheader)
    assert not app.exception
