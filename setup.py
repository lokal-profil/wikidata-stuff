from setuptools import setup
version = '0.0.1'
repo = 'wikidata-stuff'

setup(
    name='wikidataStuff',
    packages=['wikidataStuff'],
    install_requires=['pywikibot==3.0-dev', 'requests', 'MySQL-python'],
    dependency_links=['git+https://github.com/wikimedia/pywikibot-core.git#egg=pywikibot-3.0-dev'],
    version=version,
    description='Framework for mass-importing statements to Wikidata and/or for adding sources to existing statements.',
    author='Andre Costa',
    author_email='',
    url='https://github.com/lokal-profil/' + repo,
    download_url='https://github.com/lokal-profil/' + repo + '/tarball/' + version,
    keywords=['Wikidata', 'Wikimedia', 'pywikibot', 'API'],
    classifiers=[],
)
