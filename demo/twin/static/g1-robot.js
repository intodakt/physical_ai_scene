/* Unitree G1 upper-body visualization. Mount and motion are simulated, not S6 execution. */
(function(){
  const M=(x,y,z=0)=>new THREE.Vector3(-y,z,-x);
  const clamp=THREE.MathUtils.clamp;
  const mat=(color,metalness=.35,roughness=.45)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
  const bodyMat=mat(0x9babb0,.6,.36), darkMat=mat(0x34444d,.55,.42), boltMat=mat(0xcbd4d5,.75,.28);

  class G1Robot {
    constructor(scene){
      this.root=new THREE.Group();this.root.name="simulated_g1_mount";scene.add(this.root);
      this.model=null;this.joints={};this.mount={x:0.35,y:0.5,yaw:-Math.PI/2,gap:0};
      this.motion=null;this.visible=true;this.ready=false;
      const plate=new THREE.Mesh(new THREE.CylinderGeometry(.102,.115,.018,48),darkMat);
      plate.position.y=.009;plate.castShadow=true;plate.receiveShadow=true;this.root.add(plate);
      const collar=new THREE.Mesh(new THREE.CylinderGeometry(.076,.088,.074,40),bodyMat);
      collar.position.y=.055;collar.castShadow=true;this.root.add(collar);
      const hub=new THREE.Mesh(new THREE.CylinderGeometry(.078,.078,.016,40),darkMat);
      hub.position.y=.101;hub.castShadow=true;this.root.add(hub);
      for(let k=0;k<6;k++){
        const a=k*Math.PI/3,b=new THREE.Mesh(new THREE.CylinderGeometry(.006,.006,.004,12),boltMat);
        b.position.set(Math.cos(a)*.091,.019,Math.sin(a)*.091);this.root.add(b);
      }
      this.setMount(this.mount.x,this.mount.y,this.mount.yaw);
    }
    async load(){
      const [metadata,gltf]=await Promise.all([
        fetch("assets/g1/g1-upper-body.json").then(r=>{if(!r.ok)throw Error("G1 joints unavailable");return r.json();}),
        new Promise((resolve,reject)=>new THREE.GLTFLoader().load("assets/g1/g1-upper-body.glb",resolve,undefined,reject)),
      ]);
      this.model=gltf.scene;
      this.model.name="unitree_g1_upper_body";
      const basis=new THREE.Matrix4().set(0,-1,0,0, 0,0,1,0, -1,0,0,0, 0,0,0,1);
      this.model.quaternion.setFromRotationMatrix(basis);
      this.model.position.y=.107;
      this.model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
      this.root.add(this.model);
      for(const [name,meta] of Object.entries(metadata.joints)){
        const node=this.model.getObjectByName(name);
        if(node)this.joints[name]={node,base:node.quaternion.clone(),axis:new THREE.Vector3(...meta.axis).normalize(),lower:meta.lower,upper:meta.upper,value:0};
      }
      this.ready=true;
      this.home();
      return this;
    }
    setMount(x,y,yaw){
      this.mount={...this.mount,x,y,yaw};
      this.root.position.copy(M(x,y,0));this.root.rotation.y=yaw;
      this.root.updateMatrixWorld(true);
    }
    static gapAt(x,y,objects){
      return Math.min(...objects.filter(o=>!o.hidden).map(o=>{
        const radius=o.kind==="cylinder"?Number(o.size[0]):Math.hypot(Number(o.size[0]||0),Number(o.size[1]||0))/2;
        return Math.hypot(x-o.xy[0],y-o.xy[1])-radius-.115;
      }),1);
    }
    autoPlace(state){
      const objects=state.twin||[],d=state.desk||{x:[.05,1.35],y:[-.55,.55]};
      const cx=objects.reduce((n,o)=>n+o.xy[0],0)/(objects.length||1);
      const cy=objects.reduce((n,o)=>n+o.xy[1],0)/(objects.length||1);
      const candidates=[];
      for(let i=0;i<=14;i++){
        const x=d.x[0]+.08+(d.x[1]-d.x[0]-.16)*i/14;
        candidates.push([x,d.y[0]+.055],[x,d.y[1]-.055]);
        const y=d.y[0]+.08+(d.y[1]-d.y[0]-.16)*i/14;
        candidates.push([d.x[0]+.055,y],[d.x[1]-.055,y]);
      }
      let best=null,bestScore=-Infinity;
      for(const [x,y] of candidates){
        const gap=G1Robot.gapAt(x,y,objects);
        const reach=objects.filter(o=>!o.hidden&&Math.hypot(x-o.xy[0],y-o.xy[1])<.66).length;
        if(!reach)continue;
        const score=Math.min(gap,.4)*2+reach*.24+(gap>=.15?.45:0)-.12*Math.hypot(x-cx,y-cy);
        if(score>bestScore){bestScore=score;best={x,y,gap};}
      }
      if(!best)best={x:d.x[0]+.055,y:d.y[1]-.055,gap:G1Robot.gapAt(d.x[0]+.055,d.y[1]-.055,objects)};
      const yaw=Math.atan2(cy-best.y,cx-best.x);
      this.setMount(best.x,best.y,yaw);this.mount.gap=best.gap;
      this.home();
      return this.mount;
    }
    setJoint(name,value){
      const j=this.joints[name];if(!j)return;
      j.value=clamp(value,j.lower,j.upper);
      j.node.quaternion.copy(j.base).multiply(new THREE.Quaternion().setFromAxisAngle(j.axis,j.value));
    }
    values(){return Object.fromEntries(Object.entries(this.joints).map(([n,j])=>[n,j.value]));}
    apply(values){for(const [n,v] of Object.entries(values))this.setJoint(n,v);this.root.updateMatrixWorld(true);}
    home(){
      this.motion=null;
      for(const name of Object.keys(this.joints))this.setJoint(name,0);
      this.setJoint("left_shoulder_pitch_joint",.05);this.setJoint("right_shoulder_pitch_joint",.05);
      this.setJoint("left_shoulder_roll_joint",.22);this.setJoint("right_shoulder_roll_joint",-.22);
      this.setJoint("left_elbow_joint",-.15);this.setJoint("right_elbow_joint",-.15);
      for(const side of ["left","right"]){
        const bend=side==="right"?1:-1;
        for(const finger of ["index","middle"]){this.setJoint(`${side}_hand_${finger}_0_joint`,bend*.18);this.setJoint(`${side}_hand_${finger}_1_joint`,bend*.16);}
        this.setJoint(`${side}_hand_thumb_2_joint`,-bend*.12);
      }
      this.root.updateMatrixWorld(true);
      this.rest=this.values();
    }
    show(on){this.visible=on;this.root.visible=on;}
    reachTo(x,y,z){
      if(!this.ready)return {ok:false,reason:"G1 model is loading"};
      this.home();
      const target=M(x,y,Math.max(z,.055));
      const distance=Math.hypot(x-this.mount.x,y-this.mount.y);
      if(distance>.66)return {ok:false,reason:"Target is outside the mounted arm's reach"};
      const hand=(side)=>this.model.getObjectByName(`${side}_hand_palm_link`);
      const shoulder=(side)=>this.model.getObjectByName(`${side}_shoulder_pitch_joint`);
      const side=["left","right"].sort((a,b)=>shoulder(a).getWorldPosition(new THREE.Vector3()).distanceTo(target)-shoulder(b).getWorldPosition(new THREE.Vector3()).distanceTo(target))[0];
      const endpoint=hand(side);
      if(!endpoint)return {ok:false,reason:"G1 hand joint is unavailable"};
      const names=["wrist_yaw","wrist_pitch","wrist_roll","elbow","shoulder_yaw","shoulder_roll","shoulder_pitch"].map(n=>`${side}_${n}_joint`);
      for(let iter=0;iter<34;iter++){
        const error=endpoint.getWorldPosition(new THREE.Vector3()).distanceTo(target);
        if(error<.045)break;
        for(const name of names){
          const j=this.joints[name];if(!j)continue;
          const pivot=j.node.getWorldPosition(new THREE.Vector3());
          const axis=j.axis.clone().applyQuaternion(j.node.getWorldQuaternion(new THREE.Quaternion())).normalize();
          const a=endpoint.getWorldPosition(new THREE.Vector3()).sub(pivot);
          const b=target.clone().sub(pivot);
          a.addScaledVector(axis,-a.dot(axis));b.addScaledVector(axis,-b.dot(axis));
          if(a.lengthSq()<1e-8||b.lengthSq()<1e-8)continue;
          a.normalize();b.normalize();
          const angle=Math.atan2(axis.dot(new THREE.Vector3().crossVectors(a,b)),a.dot(b));
          this.setJoint(name,j.value+clamp(angle*.65,-.35,.35));
          this.root.updateMatrixWorld(true);
        }
      }
      const error=endpoint.getWorldPosition(new THREE.Vector3()).distanceTo(target);
      if(error>.075){this.home();return {ok:false,reason:"Target is outside the mounted arm's reach"};}
      const goal=this.values();
      const bend=side==="right"?1:-1;
      for(const part of ["index","middle"]){goal[`${side}_hand_${part}_0_joint`]=bend*.58;goal[`${side}_hand_${part}_1_joint`]=bend*.55;}
      goal[`${side}_hand_thumb_0_joint`]=.35;goal[`${side}_hand_thumb_1_joint`]=.32;goal[`${side}_hand_thumb_2_joint`]=-bend*.5;
      this.apply(this.rest);
      this.motion={start:performance.now(),duration:2900,from:{...this.rest},to:goal};
      return {ok:true,side,error};
    }
    update(now){
      if(!this.motion)return;
      const t=clamp((now-this.motion.start)/this.motion.duration,0,1);
      const phase=t<.43?t/.43:t<.58?1:(1-t)/.42;
      const eased=phase*phase*(3-2*phase);
      for(const [name,to] of Object.entries(this.motion.to)){
        const from=this.motion.from[name]||0;this.setJoint(name,from+(to-from)*eased);
      }
      if(t>=1){this.apply(this.rest);this.motion=null;}
    }
  }
  window.G1Robot=G1Robot;
})();
