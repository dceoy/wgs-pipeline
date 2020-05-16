#!/usr/bin/env python

import logging
import os
import sys
from itertools import chain
from pathlib import Path

import luigi
from luigi.tools import deps_tree

from .base import ShellTask
from .callcopyratiosegments import CallCopyRatioSegmentsMatched
from .canvas import CallSomaticCopyNumberVariantsWithCanvas
from .delly import CallStructualVariantsWithDelly
from .funcotator import FuncotateSegments, FuncotateVariants
from .haplotypecaller import FilterVariantTranches
from .manta import CallStructualVariantsWithManta
from .msisensor import ScoreMSIWithMSIsensor
from .mutect2 import FilterMutectCalls
from .snpeff import AnnotateVariantsWithSnpEff
from .strelka import (CallGermlineVariantsWithStrelka,
                      CallSomaticVariantsWithStrelka)


class RunVariantCaller(luigi.Task):
    ref_fa_path = luigi.Parameter()
    fq_list = luigi.ListParameter()
    cram_list = luigi.ListParameter()
    read_groups = luigi.ListParameter()
    sample_names = luigi.ListParameter()
    dbsnp_vcf_path = luigi.Parameter(default='')
    mills_indel_vcf_path = luigi.Parameter(default='')
    known_indel_vcf_path = luigi.Parameter(default='')
    hapmap_vcf_path = luigi.Parameter(default='')
    gnomad_vcf_path = luigi.Parameter(default='')
    evaluation_interval_path = luigi.Parameter(default='')
    cnv_blacklist_path = luigi.Parameter(default='')
    genomesize_xml_path = luigi.Parameter(default='')
    kmer_fa_path = luigi.Parameter(default='')
    exome_manifest_path = luigi.Parameter(default='')
    funcotator_somatic_tar_path = luigi.Parameter(default='')
    funcotator_germline_tar_path = luigi.Parameter(default='')
    snpeff_config_path = luigi.Parameter(default='')
    cf = luigi.DictParameter()
    caller = luigi.Parameter()
    annotators = luigi.ListParameter(default=list())
    normalize_vcf = luigi.BoolParameter(default=True)
    priority = luigi.IntParameter(default=1000)

    def requires(self):
        if 'germline_snv_indel.gatk' == self.caller:
            return FilterVariantTranches(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                hapmap_vcf_path=self.hapmap_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cf=self.cf
            )
        elif 'somatic_snv_indel.gatk' == self.caller:
            return FilterMutectCalls(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                gnomad_vcf_path=self.gnomad_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cf=self.cf
            )
        elif 'somatic_sv.manta' == self.caller:
            return CallStructualVariantsWithManta(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cf=self.cf
            )
        elif 'somatic_snv_indel.strelka' == self.caller:
            return CallSomaticVariantsWithStrelka(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cf=self.cf
            )
        elif 'germline_snv_indel.strelka' == self.caller:
            return CallGermlineVariantsWithStrelka(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cf=self.cf
            )
        elif 'somatic_sv.delly' == self.caller:
            return CallStructualVariantsWithDelly(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cf=self.cf
            )
        elif 'somatic_cnv.gatk' == self.caller:
            return CallCopyRatioSegmentsMatched(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cnv_blacklist_path=self.cnv_blacklist_path, cf=self.cf
            )
        elif 'somatic_cnv.canvas' == self.caller:
            return CallSomaticCopyNumberVariantsWithCanvas(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                gnomad_vcf_path=self.gnomad_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cnv_blacklist_path=self.cnv_blacklist_path,
                genomesize_xml_path=self.genomesize_xml_path,
                kmer_fa_path=self.kmer_fa_path,
                exome_manifest_path=self.exome_manifest_path, cf=self.cf
            )
        elif 'somatic_msi.msisensor' == self.caller:
            return ScoreMSIWithMSIsensor(
                fq_list=self.fq_list, cram_list=self.cram_list,
                read_groups=self.read_groups, sample_names=self.sample_names,
                ref_fa_path=self.ref_fa_path,
                dbsnp_vcf_path=self.dbsnp_vcf_path,
                mills_indel_vcf_path=self.mills_indel_vcf_path,
                known_indel_vcf_path=self.known_indel_vcf_path,
                evaluation_interval_path=self.evaluation_interval_path,
                cf=self.cf
            )
        else:
            raise ValueError(f'invalid caller: {self.caller}')

    def output(self):
        output_pos = list(
            chain.from_iterable([
                [
                    Path(self.cf[f'postproc_{k}_dir_path']).joinpath(
                        (Path(p).name + f'.{k}.tsv') if p.endswith('.seg')
                        else (Path(Path(p).stem).stem + f'.norm.{k}.vcf.gz')
                    ) for p in v
                ] for k, v in self._find_annotation_targets().items()
            ])
        )
        return (
            [luigi.LocalTarget(o) for o in output_pos]
            if output_pos else self.input()
        )

    def _find_annotation_targets(self):
        input_paths = [i.path for i in self.input()]
        if 'somatic_sv.delly' == self.caller:
            suffix_dict = {'funcotator': None, 'snpeff': '.vcf.gz'}
        elif 'somatic_sv.manta' == self.caller:
            suffix_dict = {
                'funcotator': '.manta.somaticSV.vcf.gz', 'snpeff': '.vcf.gz'
            }
        else:
            suffix_dict = {
                'funcotator': ('.vcf.gz', '.called.seg'), 'snpeff': '.vcf.gz'
            }
        return {
            k: (
                [p for p in input_paths if v and p.endswith(v)]
                if k in self.annotators else list()
            ) for k, v in suffix_dict.items()
        }

    def run(self):
        if self.annotators:
            tasks = list()
            funcotator_common_kwargs = {
                'data_src_tar_path': (
                    self.funcotator_germline_tar_path
                    if self.caller.startswith('germline_')
                    else self.funcotator_somatic_tar_path
                ),
                'ref_fa_path': self.ref_fa_path, 'cf': self.cf
            }
            for k, v in self._find_annotation_targets().items():
                if k == 'funcotator':
                    tasks.extend([
                        (
                            FuncotateSegments(
                                input_seg_path=p, **funcotator_common_kwargs
                            ) if p.endswith('.seg') else FuncotateVariants(
                                input_vcf_path=p,
                                normalize_vcf=self.normalize_vcf,
                                **funcotator_common_kwargs
                            )
                        ) for p in v
                    ])
                elif k == 'snpeff':
                    tasks.extend([
                        AnnotateVariantsWithSnpEff(
                            input_vcf_path=p,
                            snpeff_config_path=self.snpeff_config_path,
                            ref_fa_path=self.ref_fa_path, cf=self.cf,
                            normalize_vcf=self.normalize_vcf
                        ) for p in v
                    ])
            yield tasks
        else:
            pass
        logger = logging.getLogger(__name__)
        logger.debug('Task tree:' + os.linesep + deps_tree.print_tree(self))


class PrintEnvVersions(ShellTask):
    log_dir_path = luigi.Parameter()
    command_paths = luigi.ListParameter(default=list())
    run_id = luigi.Parameter(default='env')
    quiet = luigi.BoolParameter(default=False)
    priority = luigi.IntParameter(default=sys.maxsize)
    __is_completed = False

    def complete(self):
        return self.__is_completed

    def run(self):
        python = sys.executable
        self.print_log(f'Print environment versions: {python}')
        version_files = [
            Path('/proc/version'),
            *[
                o for o in Path('/etc').iterdir()
                if o.name.endswith(('-release', '_version'))
            ]
        ]
        self.setup_shell(
            run_id=self.run_id, log_dir_path=self.log_dir_path,
            commands=[python, *self.command_paths], quiet=self.quiet
        )
        self.run_shell(
            args=[
                f'{python} -m pip --version',
                f'{python} -m pip freeze --no-cache-dir'
            ]
        )
        self.run_shell(
            args=[
                'uname -a',
                *[f'cat {o}' for o in version_files if o.is_file()]
            ]
        )
        self.__is_completed = True


if __name__ == '__main__':
    luigi.run()
