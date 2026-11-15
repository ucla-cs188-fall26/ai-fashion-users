from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / 'app.py'


def start_comparison():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox[0].select('grades_by_major.csv').run()
    app.radio(key='goal').set_value('comparison')
    app.multiselect[0].set_value(['major', 'gpa']).run()
    return app


def test_comparison_workflow_revises_chart_and_keeps_choices():
    app = start_comparison()
    assert not app.exception
    assert [h.value for h in app.header][:4] == ['1. Your data', '2. What do you want to show?',
                                                  '3. Pick 1 or 2 columns', '4. Figures that fit']
    assert any(h.value == 'Bar chart' for h in app.subheader)
    app.radio(key='intent_grades_by_major.csv').set_value('variation').run()
    assert any(h.value == 'Box plot' for h in app.subheader)
    assert app.multiselect[0].value == ['major', 'gpa']
    app.radio(key='intent_grades_by_major.csv').set_value('individual').run()
    assert any(h.value == 'Strip (dot) plot' for h in app.subheader)
    assert not app.exception


def test_stated_finding_is_checked_and_drawn():
    app = start_comparison()
    app.selectbox(key='find_a_grades_by_major.csv').select('chemistry').run()
    app.selectbox(key='find_dir_grades_by_major.csv').select('lower').run()
    app.selectbox(key='find_b_grades_by_major.csv').select('english').run()
    assert not app.exception
    assert any('supports this' in s.value for s in app.success)
    assert any(h.value == '4. Your finding and figure' for h in app.header)
    assert any(h.value == 'Every value, with averages and 95% intervals' for h in app.subheader)


def test_comparing_two_measurements_routes_to_relationship():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox[0].select('grades_by_major.csv').run()
    app.radio(key='goal').set_value('comparison')
    app.multiselect[0].set_value(['gpa', 'study_hours_per_week']).run()
    assert not app.exception
    assert any('relationship' in i.value for i in app.info)
    assert any(h.value == 'Scatter plot' for h in app.subheader)
