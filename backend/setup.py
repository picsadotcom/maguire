from setuptools import setup, find_packages

setup(
    name="maguire",
    version="0.1",
    url='https://github.com/picsadotcom/maguire',
    license='BSD',
    author='Picsa',
    author_email='admin@picsa.com',
    packages=find_packages(),
    include_package_data=True,
    # dependencies are declared in requirements.in, locked in requirements.txt
    install_requires=[],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
