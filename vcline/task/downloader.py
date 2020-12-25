#!/usr/bin/env python

import re
import sys
from pathlib import Path

import luigi
from ftarc.task.downloader import DownloadAndProcessResourceFiles

from .callcopyratiosegments import PreprocessIntervals
from .core import VclineTask
from .delly import CreateExclusionIntervalListBed
from .msisensorpro import (ScanMicrosatellites,
                           UncompressEvaluationIntervalListBed)
from .resource import CreateCnvBlackListBed, CreateGnomadBiallelicSnpVcf


class WritePassingAfOnlyVcf(VclineTask):
    src_path = luigi.Parameter(default='')
    src_url = luigi.Parameter(default='')
    dest_dir_path = luigi.Parameter(default='.')
    wget = luigi.Parameter(default='wget')
    bgzip = luigi.Parameter(default='bgzip')
    n_cpu = luigi.IntParameter(default=1)
    sh_config = luigi.DictParameter(default=dict())
    priority = 10

    def output(self):
        return luigi.LocalTarget(
            Path(self.dest_dir_path).resolve().joinpath(
                Path(Path(self.src_path or self.src_url).stem).stem
                + '.af-only.vcf.gz'
            )
        )

    def run(self):
        assert bool(self.src_path or self.src_url)
        output_vcf = Path(self.output().path)
        run_id = Path(Path(output_vcf.stem).stem).stem
        message = (
            'Write a passing AF-only VCF' if self.src_path
            else 'Download a VCF file and extract passing AF-only records'
        )
        self.print_log(f'{message}:\t{run_id}')
        dest_dir = output_vcf.parent
        pyscript = Path(__file__).resolve().parent.parent.joinpath(
            'script/extract_af_only_vcf.py'
        )
        self.setup_shell(
            run_id=run_id,
            commands=[
                *(list() if self.src_path else [self.wget]), self.bgzip,
                sys.executable
            ],
            cwd=dest_dir, **self.sh_config
        )
        if self.src_path:
            src_vcf = Path(self.src_path).resolve()
        else:
            src_vcf = dest_dir.joinpath(Path(self.src_url).name)
            self.run_shell(
                args=f'set -e && {self.wget} -qSL {self.src_url} -O {src_vcf}',
                output_files_or_dirs=src_vcf
            )
        self.run_shell(
            args=(
                f'set -e && {self.bgzip}'
                + f' -@ {self.n_cpu} -dc {src_vcf}'
                + f' | {sys.executable} {pyscript} -'
                + f' | {self.bgzip} -@ {self.n_cpu} -c > {output_vcf}'
            ),
            input_files_or_dirs=src_vcf, output_files_or_dirs=output_vcf
        )


class PreprocessResources(luigi.Task):
    src_url_dict = luigi.DictParameter()
    dest_dir_path = luigi.Parameter(default='.')
    wget = luigi.Parameter(default='wget')
    bgzip = luigi.Parameter(default='bgzip')
    pbzip2 = luigi.Parameter(default='pbzip2')
    pigz = luigi.Parameter(default='pigz')
    bwa = luigi.Parameter(default='bwa')
    samtools = luigi.Parameter(default='samtools')
    tabix = luigi.Parameter(default='tabix')
    gatk = luigi.Parameter(default='gatk')
    n_cpu = luigi.IntParameter(default=1)
    memory_mb = luigi.FloatParameter(default=4096)
    use_bwa_mem2 = luigi.BoolParameter(default=False)
    sh_config = luigi.DictParameter(default=dict())
    priority = 10

    def requires(self):
        return [
            DownloadAndProcessResourceFiles(
                src_urls=[
                    v for k, v in self.src_url_dict.items()
                    if k != 'gnomad_vcf'
                ],
                dest_dir_path=self.dest_dir_path, wget=self.wget,
                bgzip=self.bgzip, pbzip2=self.pbzip2, pigz=self.pigz,
                bwa=self.bwa, samtools=self.samtools, tabix=self.tabix,
                gatk=self.gatk, n_cpu=self.n_cpu, memory_mb=self.memory_mb,
                use_bwa_mem2=self.use_bwa_mem2, sh_config=self.sh_config
            ),
            WritePassingAfOnlyVcf(
                src_url=self.src_url_dict['gnomad_vcf'],
                dest_dir_path=self.dest_dir_path, wget=self.wget,
                bgzip=self.bgzip, n_cpu=self.n_cpu, sh_config=self.sh_config
            )
        ]

    def output(self):
        path_dict = self._fetch_input_path_dict()
        fa = Path(path_dict['ref_fa'])
        interval = Path(path_dict['evaluation_interval'])
        gnomad_vcf = Path(path_dict['gnomad_vcf'])
        cnv_blacklist = Path(path_dict['cnv_blacklist'])
        return [
            *self.input(),
            *[
                luigi.LocalTarget(
                    interval.parent.joinpath(interval.stem + s)
                ) for s in [
                    '.bed', '.bed.gz', '.bed.gz.tbi', '.exclusion.bed.gz',
                    '.exclusion.bed.gz.tbi', '.preprocessed.wes.interval_list',
                    '.preprocessed.wgs.interval_list'
                ]
            ],
            *[
                luigi.LocalTarget(
                    gnomad_vcf.parent.joinpath(
                        Path(gnomad_vcf.stem).stem + '.biallelic_snp' + s
                    )
                ) for s in ['.vcf.gz', '.vcf.gz.tbi']
            ],
            *[
                luigi.LocalTarget(
                    cnv_blacklist.parent.joinpath(cnv_blacklist.stem + s)
                ) for s in ['.bed.gz', '.bed.gz.tbi']
            ],
            luigi.LocalTarget(
                fa.parent.joinpath(fa.stem + '.microsatellites.tsv')
            )
        ]

    def run(self):
        path_dict = self._fetch_input_path_dict()
        cf = {
            'pigz': self.pigz, 'pbzip2': self.pbzip2, 'bgzip': self.bgzip,
            'bwa': self.bwa, 'samtools': self.samtools, 'tabix': self.tabix,
            'gatk': self.gatk, 'use_bwa_mem2': self.use_bwa_mem2
        }
        yield [
            CreateExclusionIntervalListBed(
                evaluation_interval_path=path_dict['evaluation_interval'],
                cf=cf, n_cpu=self.n_cpu, sh_config=self.sh_config
            ),
            CreateGnomadBiallelicSnpVcf(
                gnomad_vcf_path=path_dict['gnomad_vcf'],
                ref_fa_path=path_dict['ref_fa'],
                evaluation_interval_path=path_dict['evaluation_interval'],
                cf=cf, n_cpu=self.n_cpu, memory_mb=self.memory_mb,
                sh_config=self.sh_config
            ),
            CreateCnvBlackListBed(
                cnv_blacklist_path=path_dict['cnv_blacklist'], cf=cf,
                n_cpu=self.n_cpu, sh_config=self.sh_config
            ),
            *[
                PreprocessIntervals(
                    ref_fa_path=path_dict['ref_fa'],
                    evaluation_interval_path=path_dict['evaluation_interval'],
                    cnv_blacklist_path=path_dict['cnv_blacklist'],
                    cf={'exome': bool(i), **cf}, n_cpu=self.n_cpu,
                    memory_mb=self.memory_mb, sh_config=self.sh_config
                ) for i in range(2)
            ],
            ScanMicrosatellites(
                ref_fa_path=path_dict['ref_fa'], cf=cf, n_cpu=self.n_cpu,
                sh_config=self.sh_config
            ),
            UncompressEvaluationIntervalListBed(
                evaluation_interval_path=path_dict['evaluation_interval'],
                cf=cf, n_cpu=self.n_cpu, sh_config=self.sh_config
            )
        ]

    def _fetch_input_path_dict(self):
        dest_dir = Path(self.dest_dir_path).resolve()
        return {
            **{
                k: re.sub(
                    r'\.(gz|bz2)$', '',
                    str(dest_dir.joinpath(Path(self.src_url_dict[k]).name))
                ) for k in ['ref_fa', 'evaluation_interval', 'cnv_blacklist']
            },
            'gnomad_vcf': self.input()[1].path
        }


if __name__ == '__main__':
    luigi.run()
