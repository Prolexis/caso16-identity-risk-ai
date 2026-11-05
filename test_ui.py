from streamlit.testing.v1 import AppTest

at = AppTest.from_file('app.py', default_timeout=30)
at.run()
assert not at.exception
assert len(at.text_input) == 1
at.text_input[0].set_value('demo')
at.button[0].click().run()
assert not at.exception, [str(x.value) for x in at.exception]
print('after_login', len(at.title), len(at.radio), len(at.metric), len(at.dataframe))
print('titles', [x.value for x in at.title])
