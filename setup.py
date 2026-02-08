from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='vtop',
    version='1.0.0',
    author='Filippo Vicidomini',
    author_email='',
    description='Advanced system monitor for Apple Silicon Macs with per-core CPU tracking',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/filippovicidomini/vtop',
    packages=find_packages(),
    install_requires=[
        'dashing',
        'psutil',
    ],
    entry_points={
        'console_scripts': [
            'vtop=vtop.vtop:main',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: System :: Monitoring',
    ],
    keywords='apple silicon m1 m2 m3 m4 mac monitor cpu gpu performance terminal',
)
