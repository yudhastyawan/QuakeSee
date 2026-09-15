from setuptools import setup, find_packages

setup(
    name='quakesee',
    version='1.0.1',
    description='QuakeSee - Earthquake Analysis Tool',
    author='Yudha Styawan',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'quakesee=quakesee.quakesee:main',
        ],
    },
    install_requires=[
        'pyqt>=5.15.9',
        'cryptography>=3.3',
        'paramiko>=3.3.1',
        'geopandas==0.12.2',
        'matplotlib==3.7.0',
        'numpy==1.24.2',
        'obspy==1.4.0',
        'pandas==1.5.3',
        'qtconsole==5.4.0',
        'scipy==1.10.0',
        'shapely==2.0.1',
        'pyyaml==6.0',
        'sympy==1.12',
        'fiona<1.9.0',
        'setuptools<70'
    ]
)
