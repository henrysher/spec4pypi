import os

from tarfile import TarFile
from zipfile import ZipFile

import pytest

from flexmock import flexmock

from pyp2rpm.archive import Archive
from pyp2rpm.metadata_extractors import *
from pyp2rpm.name_convertor import NameConvertor
from pyp2rpm import settings

tests_dir = os.path.split(os.path.abspath(__file__))[0]

class TestMetadataExtractor(object):
    td_dir = '{0}/test_data/'.format(tests_dir)

    def setup_method(self, method):
        # create fresh extractors for every test

        self.nc = NameConvertor('fedora')
        self.e = [LocalMetadataExtractor('{0}plumbum-0.9.0.tar.gz'.format(self.td_dir), 'plumbum', self.nc, '0.9.0'),
                  LocalMetadataExtractor('{0}pytest-2.2.3.zip'.format(self.td_dir), 'pytest', self.nc, '2.2.3'),
                  LocalMetadataExtractor('{0}restsh-0.1.tar.gz'.format(self.td_dir), 'restsh', self.nc, '0.1'),
                  LocalMetadataExtractor('{0}Sphinx-1.1.3-py2.6.egg'.format(self.td_dir), 'Sphinx', self.nc, '1.1.3'),
                  LocalMetadataExtractor('{0}unextractable-1.tar'.format(self.td_dir), 'unextractable', self.nc, '1'),
                  LocalMetadataExtractor('{0}bitarray-0.8.0.tar.gz'.format(self.td_dir), 'bitarray', self.nc, '0.8.0'),
                  LocalMetadataExtractor('{0}versiontools-1.9.1.tar.gz'.format(self.td_dir), 'versiontools', self.nc, '1.9.1'),
                 ]

    @pytest.mark.parametrize(('lst', 'expected'), [
        ([['Requires', 'pyfoo', 'spam', 'spam']], [['Requires', 'pyfoo', 'spam', 'spam']]),
        ([['Requires', 'foo', 'spam', 'spam']], [['Requires', 'python-foo', 'spam', 'spam']]),
        ([['Requires', 'foo-python']], [['Requires', 'python-foo']]),
        ([['Requires', 'python-foo', 'spam']], [['Requires', 'python-foo', 'spam']]),
    ])
    def test_name_convert_deps_list(self, lst, expected):
        assert self.e[0].name_convert_deps_list(lst) == expected

    def test_runtime_deps_from_egg_info_no_deps(self):
        flexmock(Archive).should_receive('get_content_of_file').with_args('EGG-INFO/requires.txt', True).and_return('')
        assert self.e[3].runtime_deps_from_egg_info == []

    def test_runtime_deps_from_egg_info_some_deps(self):
        flexmock(Archive).should_receive('get_content_of_file').with_args('EGG-INFO/requires.txt', True).and_return('spam>1.0\n\n')
        assert len(self.e[3].runtime_deps_from_egg_info) == 1

    @pytest.mark.parametrize(('i', 'expected'), [
        (0, True),
        (1, True),
        (3, False),
        (4, False),
    ])
    def test_has_bundled_egg_info(self, i, expected):
        with self.e[i].archive:
            assert self.e[i].has_bundled_egg_info == expected

    @pytest.mark.parametrize(('i', 'expected'), [
        (0, False),
        (3, False),
        (4, False),
        (5, True),
    ])
    def test_has_extension(self, i, expected):
        with self.e[i].archive:
            assert self.e[i].has_extension == expected
    @pytest.mark.parametrize(('i', 'expected'), [
        (0, ['README.rst', 'LICENSE']),
        (1, ['README.txt', 'LICENSE']),
        (3, []),
    ])
    def test_doc_files(self, i, expected):
        with self.e[i].archive:
            assert self.e[i].doc_files == expected

    @pytest.mark.parametrize(('i', 'expected'), [
        (0, None),
        (6, 'versiontools-1.9.1/doc'),
    ])
    def test_sphinx_dir(self, i, expected):
        with self.e[i].archive:
            assert self.e[i].sphinx_dir == expected

class TestPypiMetadataExtractor(object):
    td_dir = '{0}/test_data/'.format(tests_dir)
    client = flexmock(
        release_urls = lambda n, v: [{'md5_digest': '9a7a2f6943baba054cf1c28e05a9198e',
                                      'url': 'http://pypi.python.org/packages/source/r/restsh/restsh-0.1.tar.gz'}],
        release_data = lambda n, v: {'description': 'UNKNOWN',
                                     'release_url': 'http://pypi.python.org/pypi/restsh/0.1',
                                     'classifiers': ['Development Status :: 4 - Beta',
                                                     'Intended Audience :: Developers',
                                                     'License :: OSI Approved :: BSD License',
                                                     'Operating System :: OS Independent'
                                                     ],
                                     'license': 'BSD',
                                     'summary': 'A simple rest shell client',
                                     'spam': 'eggs and beans'
                                    }
    )

    def setup_method(self, method):
        self.nc = NameConvertor('fedora')
        # we will only test getting stuff from the client => pass spam as file
        self.e = PypiMetadataExtractor('spam', 'restsh', self.nc, '0.1', self.client)

    @pytest.mark.parametrize(('what', 'expected'), [
        ('description', 'UNKNOWN'),
        ('md5','9a7a2f6943baba054cf1c28e05a9198e'),
        ('url', 'http://pypi.python.org/packages/source/r/restsh/restsh-0.1.tar.gz'),
        ('license', 'BSD'),
        ('summary', 'A simple rest shell client')
    ])
    def test_extract(self, what, expected):
        data = self.e.extract_data()
        assert getattr(data, what) == expected

class TestLocalMetadataExtractor(object):
    td_dir = '{0}/test_data/'.format(tests_dir)

    def setup_method(self, method): # test for non-egg and egg
        self.nc = NameConvertor('fedora')
        self.e = [LocalMetadataExtractor('{0}plumbum-0.9.0.tar.gz'.format(self.td_dir), 'plumbum', self.nc, '0.9.0'),
                  LocalMetadataExtractor('{0}Sphinx-1.1.3-py2.6.egg'.format(self.td_dir), 'Sphinx', self.nc, '1.1.3')
                 ]

    @pytest.mark.parametrize(('i', 'what', 'expected'), [
        (0, 'description', 'TODO:'), # try random non-set attribute
        (0, 'license','MIT'),
        (1, 'license', 'BSD'),
    ])
    def test_extract(self, i, what, expected):
        data = self.e[i].extract_data()
        assert getattr(data, what) == expected
