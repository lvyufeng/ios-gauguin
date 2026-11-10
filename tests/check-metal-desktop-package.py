#!/usr/bin/env python3
"""Inspect real packaged binaries with system tools and reject mismatched contracts."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,stat,subprocess
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--recipe',type=Path,required=True)
    ap.add_argument('--package',type=Path,required=True);a=ap.parse_args();repo=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('package',repo/'tools/prepare-metal-desktop-package.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    proofs,_=module.read_proofs(json.loads(a.recipe.read_text()));module.validate_contract(proofs,repo)
    bad=[]
    def add(name,mutate):
        value=copy.deepcopy(proofs);mutate(value)
        try:module.validate_contract(value,repo)
        except ValueError:bad.append(name)
        else:raise AssertionError('corrupt contract accepted: '+name)
    add('wrong-core',lambda x:x['core'].update(sha256='0'*64))
    add('root-only-frontend',lambda x:x['frontend'].update(desktop_candidate=False))
    add('wrong-plugin-class',lambda x:x['frontend']['discovery_install'].update(MetalPluginClassName='HakiosMetalDevice'))
    add('root-cache-for-mobile',lambda x:x['frontend'].update(cache='/private/var/db/hakios-metal-cache'))
    add('shared-root-pipeline-cache',lambda x:x['frontend'].update(pipeline_cache='/private/var/tmp/hakios-pipelinelib'))
    add('delayed-root-bootstrap',lambda x:x['bootstrap'].update(initial_delay_seconds=90))
    add('wrong-wire-selector',lambda x:x['bootstrap'].update(required_kernel_selector=0x7b))
    add('missing-clean-handoff',lambda x:x['bootstrap'].update(requires_clean_armed_owner_close=False))
    add('wrong-SETEXEC-target',lambda x:x['router']['targets'][0].update(argument='--metal226'))
    add('installed237-instead-of240',lambda x:x['retained'].update(sha256='d1f08acbb2dbc71265023fd151fd7e224cc82b4e76fd524dcc79e32e7840a47f'))
    add('dropped-task',lambda x:x['launch'].update(total_jobs=530))
    add('changed-unrelated-job',lambda x:x['launch'].update(unchanged_jobs=528))
    add('lost-fallback-marker',lambda x:x['launch'].update(retained_admission_marker=False))
    add('lost-fresh-capture-requirement',lambda x:x['system'].update(fresh_post240_capture_required=False))
    qc='/System/Library/Frameworks/QuartzCore.framework/default.metallib'
    add('foreign-QuartzCore-library',lambda x:x['system']['files'][qc].update(sha256='0'*64))
    add('foreign-pipeline-functions',lambda x:x['system']['files']['/System/Library/Frameworks/QuartzCore.framework/default.pipelinelib/functions'].update(sha256='0'*64))
    add('unwritable-mobile-parent',lambda x:x['system']['files']['/private/var/mobile/Library/Caches'].update(mode=0o40555))
    add('wrong-OS',lambda x:x['system'].update(OS_build='20F66'))
    add('old-kernel-source',lambda x:x['kernel'].update(source_sha256='f002053dffd1b6f0a152a8bbb22e193cfb242b971c61d30e05402ca49e2a8b44'))
    add('failed-link',lambda x:x['kernel'].update(make_exit=1))
    add('missing-final-kernel',lambda x:x['kernel'].update(final_kernel_produced=False))
    add('unqualified-board-base',lambda x:x['base'].update(image_sha256='0'*64))
    add('missing-physical-base-proof',lambda x:x['base_acceptance'].update(input_RO_hardware_qualified=False))
    package=json.loads((a.package/'result.json').read_text());root=(a.package/'root').resolve()
    assert package['state']=='complete-local-desktop-candidate-not-volume-or-phone-qualified'
    assert not package['installed']and not package['volume_staged']and not package['installation_ready']
    assert package['requires_0240_installed_and_paired_trial']and package['requires_fresh_post240_capture']
    assert package['requires_deduplicated_boot_key_replacement']and package['qualified_board_arguments_must_be_preserved']
    assert package['command_bytes']==len(package['command'].encode())<=1023
    for name,value in package['software_boot_argument_overrides'].items():
        assert package['command'].split().count(name+'='+str(value))==1
    assert package['parent_directory_metadata_must_be_preserved']and package['payload_owner_is_not_installation_owner']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    actual={str(p.relative_to(root))for p in root.rglob('*')if p.is_file()}
    assert len(package['files'])==7 and actual=={p.lstrip('/')for p in package['files']}
    assert len({p.casefold()for p in package['files']})==7
    for dest,row in package['files'].items():
        path=Path(row['path']);assert path.resolve()==root/dest.lstrip('/')and not path.is_symlink()
        assert path.stat().st_size==row['bytes']and sha(path)==row['sha256']
        assert row['target_uid']==row['target_gid']==0 and stat.S_IMODE(path.stat().st_mode)==stat.S_IMODE(row['target_mode'])
    for name,loads in package['dependencies'].items():
        src={'core':'library','frontend':'binary','retained':'probe','bootstrap':'binary','router':'binary'}[name]
        original=Path(proofs[name][src])
        packaged=next(Path(row['path'])for row in package['files'].values()if row['sha256']==sha(original))
        output=subprocess.check_output(['otool','-L',str(packaged)],text=True)
        actual=[s.strip().split(' (compatibility version')[0]for s in output.splitlines()[1:]]
        assert actual==loads['identity']+loads['dependencies'],(name,actual,loads)
    cache=package['directories']['/private/var/mobile/Library/Caches/gauguin-metal244']
    assert cache==dict(target_uid=501,target_gid=501,target_mode=0o40700)
    assert stat.S_IMODE((root/'private/var/mobile/Library/Caches/gauguin-metal244').stat().st_mode)==0o700
    for row in package['launch_templates'].values():
        p=Path(row['path']);assert not p.resolve().is_relative_to(root)
        assert sha(p)==row['sha256']and row['requires_post240_regeneration']
    kernel=package['kernel'];assert sha(Path(kernel['path']))==kernel['sha256']==proofs['kernel']['kernel_sha256']
    assert kernel['source_sha256']==module.SOURCE
    for n,h in package['input_pins'].items():assert sha(Path(n))==h
    print('PASS real package: seven root files, native dependency tables, target metadata, separate launch templates, kernel digest; '+str(len(bad))+' mismatched contracts rejected; no phone result')
if __name__=='__main__':main()
