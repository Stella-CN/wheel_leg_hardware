from pathlib import Path
import sys,json,math,hashlib,time,shutil
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'tools'))
import build_printable_robot as cad
import analyze_v5_motor_load as load
p=root/'mechanical/v5/wheel_leg_v5.FCStd';bpath=root/'mechanical/v5/mass_budget.json'
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
original_sha=sha(p);snapshot=Path('/tmp/v5_native_gravity_snapshot.FCStd');shutil.copy2(p,snapshot);budget=json.loads(bpath.read_text());doc=cad.App.openDocument(str(snapshot))
missing=[];refs=[];centroids={};local_center_discrepancies=[]
for row in budget['parts']:
    obj=doc.getObject(row['part'])
    if obj is None:
        if row['material']!='allowance':missing.append(row['part'])
    refs.append((row,obj))
    if obj is not None:
        solids=obj.Shape.Solids
        vol=sum(part.Volume for part in solids)
        center=sum((part.CenterOfMass*part.Volume for part in solids),cad.V())/vol
        centroids[obj.Name]=obj.Placement.inverse().multVec(center)
        local_center_discrepancies.append((centroids[obj.Name]-cad.V(*row['local_center_mm'])).Length)
assert not missing,missing
# Native Shape contains live Placement; no local_center_mm or role equations used below.
def energy(ell_mm,beta_rad):
    doc.Parameters.LegLength=ell_mm;doc.Parameters.Beta=math.degrees(beta_rad);doc.recompute()
    total=0.
    for row,obj in refs:
        if obj is None:z=row['center_mm'][2]
        else:
            z=obj.Placement.multVec(centroids[obj.Name]).z
        total+=row['mass_g']/1000*9.81*(z+ell_mm*math.cos(beta_rad))/1000
    return total
lengths=[120.,183.8477631085,225.]
reference=load.distributed_gravity(budget,[value/1000 for value in lengths])['rows']
results=[]
for length,ref in zip(lengths,reference):
    alpha=math.acos(length/260.)
    alpha_prime=-1/(260*math.sin(alpha))  # rad/mm
    estimates=[]
    for dell,dbeta in ((.002,2e-5),(.001,1e-5)):
        uL=(energy(length+dell,0)-energy(length-dell,0))/(2*dell)
        uB=(energy(length,dbeta)-energy(length,-dbeta))/(2*dbeta)
        hip=uB/2
        knee=uL/(4*alpha_prime)+hip/2
        estimates.append(dict(dell_mm=dell,dbeta_rad=dbeta,dU_dell_J_per_mm=uL,dU_dbeta_J_per_rad=uB,
                              hip_gravity_Nm=hip,knee_gravity_Nm=knee))
    row=dict(leg_length_mm=length,native_energy_J=energy(length,0),native_differences=estimates,
             analytic_role_based_reference=ref,
             hip_error_Nm=estimates[-1]['hip_gravity_Nm']-ref['hip_gravity_Nm'],
             knee_error_Nm=estimates[-1]['knee_gravity_Nm']-ref['knee_gravity_Nm'],
             native_step_convergence_Nm=max(abs(estimates[0][k]-estimates[1][k]) for k in ('hip_gravity_Nm','knee_gravity_Nm')))
    results.append(row);print(json.dumps(row),flush=True)
doc.Parameters.LegLength=183.8477631085;doc.Parameters.Beta=0;doc.recompute()
# Deliberately close without save; shape/parameter perturbations stay in memory.
cad.App.closeDocument(doc.Name)
assert original_sha==sha(snapshot),'Read-only validation changed snapshot'
report=dict(method='Independent finite differences of native FreeCAD parameter expressions; no role transform or local-COM equations reused.',
   potential='sum m*g*(native_shape_CoM_z + ell*cos(Beta)); SI potential units',
   coordinates='qhip=Beta-alpha; qknee=2alpha-pi; alpha=acos(ell/(2L)); 2 symmetric drives per coordinate',
   chain_rule=dict(dU_dBeta='2*tau_hip',dU_dell='-2*alpha_prime*tau_hip + 4*alpha_prime*tau_knee',
                   tau_hip='0.5*dU_dBeta',tau_knee='dU_dell/(4*alpha_prime)+tau_hip/2'),
   mass_budget_kg=budget['total_kg'],objects_with_native_mass_centers=sum(obj is not None for _,obj in refs),
   unmodelled_allowance_g=sum(row['mass_g'] for row,obj in refs if obj is None),
   assembly_snapshot_sha256_before=original_sha,assembly_snapshot_sha256_after=sha(snapshot),source_assembly_sha256_after=sha(p),
   source_changed_externally_during_review=original_sha!=sha(p),maximum_cached_native_vs_budget_local_centroid_error_mm=max(local_center_discrepancies),
   native_centroid_method='Re-integrate every native solid once; transform cached centroid with perturbed native object Placement. No role-specific transform is reused.',mass_budget_sha256=sha(bpath),
   load_algorithm_sha256=sha(root/'tools/analyze_v5_motor_load.py'),rows=results,
   maximum_absolute_error_Nm=max(abs(row[key]) for row in results for key in ('hip_error_Nm','knee_error_Nm')),
   tolerance_Nm=1e-5,scope='Distributed gravity only: no inertia, contact dynamics, true motor internal COM, friction, balance controller or thermal validation.')
report['passed']=report['maximum_absolute_error_Nm']<report['tolerance_Nm']
(root/'mechanical/v5/distributed_gravity_native_review.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASSED',report['passed'],'MAX_ERROR_NM',report['maximum_absolute_error_Nm'],flush=True)
