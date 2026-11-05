from streamlit.testing.v1 import AppTest
at=AppTest.from_file('app.py', default_timeout=30)
at.run()
at.text_input[0].set_value('demo')
at.button[0].click().run()
at.radio[0].set_value('Reportes').run()
print('reports', len(at.download_button), len(at.exception))
print('errors', [str(x.value) for x in at.exception])
