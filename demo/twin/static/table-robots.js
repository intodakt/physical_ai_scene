/* Detailed table arm and mobile robot. Their motion is a visual simulation, not hardware control. */
(function(){
  const M=(x,y,z=0)=>new THREE.Vector3(-y,z,-x);
  const clamp=THREE.MathUtils.clamp;
  const smooth=t=>{t=clamp(t,0,1);return t*t*(3-2*t);};
  const finish=(a,b,t)=>a+(b-a)*smooth(clamp(t,0,1));
  const shell=new THREE.MeshStandardMaterial({color:0xd1d7d5,metalness:.34,roughness:.34});
  const alloy=new THREE.MeshStandardMaterial({color:0x78878a,metalness:.57,roughness:.3});
  const graphite=new THREE.MeshStandardMaterial({color:0x29363b,metalness:.38,roughness:.43});
  const rubber=new THREE.MeshStandardMaterial({color:0x1a2023,metalness:.04,roughness:.88});
  const trim=new THREE.MeshStandardMaterial({color:0x1e6470,metalness:.3,roughness:.37});
  const glass=new THREE.MeshStandardMaterial({color:0x122832,metalness:.35,roughness:.16,emissive:0x09232d,emissiveIntensity:.25});
  const bolt=new THREE.MeshStandardMaterial({color:0xa8b3b5,metalness:.75,roughness:.23});
  const add=(parent,geometry,material,x=0,y=0,z=0)=>{
    const mesh=new THREE.Mesh(geometry,material);mesh.position.set(x,y,z);
    mesh.castShadow=true;mesh.receiveShadow=true;parent.add(mesh);return mesh;
  };
  const box=(parent,w,h,d,material,x=0,y=0,z=0)=>add(parent,new THREE.BoxGeometry(w,h,d),material,x,y,z);
  const cyl=(parent,top,bottom,height,material,x=0,y=0,z=0,segments=32)=>add(parent,new THREE.CylinderGeometry(top,bottom,height,segments),material,x,y,z);
  const ball=(parent,r,material,x=0,y=0,z=0)=>add(parent,new THREE.SphereGeometry(r,20,12),material,x,y,z);
  function ring(parent,r,t,material,y){const m=add(parent,new THREE.TorusGeometry(r,t,8,40),material,0,y,0);m.rotation.x=Math.PI/2;return m;}
  function cable(parent,points,r=.003){
    const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));
    add(parent,new THREE.TubeGeometry(curve,24,r,7,false),rubber);
  }
  function joint(parent,r){
    const hub=cyl(parent,r,r,.055,graphite);hub.rotation.z=Math.PI/2;
    for(const s of [-1,1]){
      const cap=cyl(parent,r*.72,r*.72,.004,alloy,s*.029,0,0);cap.rotation.z=Math.PI/2;
      const axle=cyl(parent,r*.27,r*.27,.005,bolt,s*.032,0,0);axle.rotation.z=Math.PI/2;
      for(let k=0;k<4;k++){
        const a=k*Math.PI/2+.3;
        const screw=cyl(parent,.0025,.0025,.002,bolt,s*.033,Math.cos(a)*r*.51,Math.sin(a)*r*.51,10);
        screw.rotation.z=Math.PI/2;
      }
    }
  }
  function link(parent,length,radius){
    const core=cyl(parent,radius*.86,radius,length*.86,shell,0,0,-length/2);
    core.rotation.x=Math.PI/2;
    const spine=box(parent,radius*.87,radius*.44,length*.74,alloy,0,-radius*.77,-length/2);
    spine.material=alloy;
    for(const x of [-1,1]){
      const rail=box(parent,.005,.011,length*.7,graphite,x*radius*.67,0,-length/2);
      rail.position.y=radius*.18;
    }
    cable(parent,[[radius*.72,-.001,-.025],[radius*.89,.006,-length*.35],[radius*.83,-.002,-length*.78],[radius*.56,-.006,-length+.01]],.0024);
  }

  class TableRobots {
    constructor(scene){
      this.scene=scene;this.mode="arm";this.ready=true;
      this.mount={x:.7,y:-.5,yaw:Math.PI*.75,gap:0};this.start=[.22,0];
      this.motion=null;this.held=null;
      this.armRoot=new THREE.Group();this.armRoot.name="desk_arm";scene.add(this.armRoot);
      this.roverRoot=new THREE.Group();this.roverRoot.name="mobile_robot";scene.add(this.roverRoot);
      this.root=this.armRoot;
      this.buildArm();this.buildRover();this.setMount(this.mount.x,this.mount.y,this.mount.yaw);
      this.setStart(this.start);this.home();this.show("arm");
    }
    load(){return Promise.resolve(this);}
    buildArm(){
      const root=this.armRoot;
      cyl(root,.081,.088,.014,graphite,0,.007,0,48);
      cyl(root,.065,.068,.007,alloy,0,.018,0,48);
      ring(root,.073,.002,bolt,.017);
      for(let i=0;i<6;i++){
        const a=i*Math.PI/3;
        cyl(root,.003,.003,.003,bolt,Math.cos(a)*.073,.019,Math.sin(a)*.073,12);
      }
      const yaw=new THREE.Group();yaw.position.y=.025;root.add(yaw);this.yaw=yaw;
      cyl(yaw,.051,.056,.07,shell,0,.035,0,40);
      ring(yaw,.046,.002,graphite,.07);
      box(yaw,.037,.014,.025,graphite,0,.071,-.031);
      const shoulder=new THREE.Group();shoulder.position.y=.13;yaw.add(shoulder);this.shoulder=shoulder;
      joint(shoulder,.039);
      link(shoulder,.27,.028);
      const elbow=new THREE.Group();elbow.position.z=-.27;shoulder.add(elbow);this.elbow=elbow;
      joint(elbow,.033);
      link(elbow,.265,.023);
      const wrist=new THREE.Group();wrist.position.z=-.265;elbow.add(wrist);this.wrist=wrist;
      joint(wrist,.025);
      const collar=cyl(wrist,.022,.021,.038,alloy,0,0,-.025);collar.rotation.x=Math.PI/2;
      box(wrist,.071,.023,.037,graphite,0,0,-.055);
      box(wrist,.056,.004,.03,alloy,0,.014,-.055);
      this.armFingers=[];
      for(const s of [-1,1]){
        const finger=new THREE.Group();finger.position.set(s*.032,0,-.075);wrist.add(finger);
        box(finger,.010,.023,.037,shell,0,0,-.017);
        box(finger,.012,.017,.020,rubber,-s*.001,-.003,-.038);
        cyl(finger,.004,.004,.004,bolt,0,.014,-.006,12);
        this.armFingers.push({group:finger,side:s});
      }
      this.armTip=new THREE.Object3D();this.armTip.position.set(0,0,-.105);wrist.add(this.armTip);
    }
    buildRover(){
      const root=this.roverRoot;
      box(root,.145,.033,.17,graphite,0,.039,0);
      box(root,.127,.017,.152,shell,0,.064,0);
      box(root,.09,.005,.10,alloy,0,.075,.012);
      for(const s of [-1,1])for(const end of [-1,1]){
        const wheel=cyl(root,.022,.022,.018,rubber,s*.078,.023,end*.061,32);wheel.rotation.z=Math.PI/2;
        const hub=cyl(root,.010,.010,.019,alloy,s*.08,.023,end*.061,24);hub.rotation.z=Math.PI/2;
        const axle=cyl(root,.004,.004,.02,bolt,s*.082,.023,end*.061,16);axle.rotation.z=Math.PI/2;
      }
      box(root,.111,.015,.012,alloy,0,.042,-.087);
      box(root,.064,.022,.008,glass,0,.066,-.084);
      for(const s of [-1,1])ball(root,.004,trim,s*.031,.069,-.089);
      cyl(root,.023,.024,.007,graphite,0,.083,.016,32);
      cyl(root,.017,.017,.018,alloy,0,.096,.016,32);
      cyl(root,.015,.015,.008,glass,0,.11,.016,32);
      ring(root,.016,.0015,bolt,.105);
      for(const s of [-1,1]){
        box(root,.015,.004,.048,alloy,s*.049,.078,.006);
        box(root,.013,.003,.025,graphite,s*.049,.081,.006);
        box(root,.007,.062,.012,alloy,s*.026,.078,-.087);
      }
      const gripper=new THREE.Group();gripper.position.set(0,.053,-.087);root.add(gripper);this.roverGripper=gripper;
      box(gripper,.038,.014,.041,alloy,0,0,-.021);
      this.roverFingers=[];
      for(const s of [-1,1]){
        const finger=new THREE.Group();finger.position.set(s*.019,0,-.045);gripper.add(finger);
        box(finger,.007,.014,.034,shell,0,0,-.014);
        box(finger,.008,.010,.013,rubber,-s*.001,-.002,-.035);
        this.roverFingers.push({group:finger,side:s});
      }
      this.roverTip=new THREE.Object3D();this.roverTip.position.set(0,0,-.078);gripper.add(this.roverTip);
      this.wheels=root.children.filter(o=>o.isMesh&&o.material===rubber&&o.geometry.type==="CylinderGeometry");
    }
    setMount(x,y,yaw){
      this.mount={...this.mount,x,y,yaw};this.armRoot.position.copy(M(x,y,0));this.armRoot.rotation.y=yaw;
      this.armRoot.updateMatrixWorld(true);
    }
    setStart(start){
      if(Array.isArray(start)&&start.length>=2)this.start=[+start[0],+start[1]];
      this.roverRoot.position.copy(M(...this.start));this.roverRoot.rotation.y=0;
    }
    static gapAt(x,y,objects){
      return Math.min(...objects.filter(o=>!o.hidden).map(o=>{
        const radius=o.kind==="cylinder"?Number(o.size[0]):Math.hypot(Number(o.size[0]||0),Number(o.size[1]||0))/2;
        return Math.hypot(x-o.xy[0],y-o.xy[1])-radius-.09;
      }),1);
    }
    autoPlace(state){
      const objects=state.twin||[],d=state.desk||{x:[.05,1.35],y:[-.55,.55]};
      const cx=objects.reduce((n,o)=>n+o.xy[0],0)/(objects.length||1);
      const cy=objects.reduce((n,o)=>n+o.xy[1],0)/(objects.length||1);
      let best=null,bestScore=-Infinity,fallback=null;
      for(let i=0;i<=14;i++){
        const x=d.x[0]+.07+(d.x[1]-d.x[0]-.14)*i/14;
        const y=d.y[0]+.07+(d.y[1]-d.y[0]-.14)*i/14;
        for(const [px,py] of [[x,d.y[0]+.07],[x,d.y[1]-.07],[d.x[0]+.07,y],[d.x[1]-.07,y]]){
          const gap=TableRobots.gapAt(px,py,objects);
          if(!fallback||gap>fallback.gap)fallback={x:px,y:py,gap};
          const reach=objects.filter(o=>!o.hidden&&Math.hypot(px-o.xy[0],py-o.xy[1])<.60).length;
          if(!reach||gap<.12)continue;
          const score=Math.min(gap,.4)*2+reach*.24+.45-.12*Math.hypot(px-cx,py-cy);
          if(score>bestScore){bestScore=score;best={x:px,y:py,gap};}
        }
      }
      if(!best)best=fallback;
      this.setMount(best.x,best.y,Math.atan2(cy-best.y,cx-best.x));this.mount.gap=best.gap;
      this.home();return this.mount;
    }
    show(mode){this.mode=mode;this.armRoot.visible=mode==="arm";this.roverRoot.visible=mode==="rover";}
    pose(){return {yaw:this.yaw.rotation.y,shoulder:this.shoulder.rotation.x,elbow:this.elbow.rotation.x,wrist:this.wrist.rotation.x,grip:this.grip||0};}
    applyPose(p){
      this.yaw.rotation.y=p.yaw;this.shoulder.rotation.x=p.shoulder;this.elbow.rotation.x=p.elbow;this.wrist.rotation.x=p.wrist;
      this.grip=p.grip;
      for(const {group,side} of this.armFingers)group.position.x=side*(.032-.014*p.grip);
      this.armRoot.updateMatrixWorld(true);
    }
    applyRoverGrip(t){this.roverGrip=t;for(const {group,side} of this.roverFingers)group.position.x=side*(.019-.008*t);}
    home(){
      this.motion=null;this.held=null;this.applyPose({yaw:0,shoulder:1.1,elbow:-1,wrist:-.1,grip:0});
      this.setStart(this.start);this.roverGripper.position.set(0,.053,-.087);this.applyRoverGrip(0);
    }
    release(){this.home();}
    handPosition(side){
      const tip=side==="rover"?this.roverTip:this.armTip;
      return tip.getWorldPosition(new THREE.Vector3());
    }
    solveArm(x,y,z){
      const target=this.armRoot.worldToLocal(M(x,y,z).clone());
      const yaw=Math.atan2(-target.x,-target.z),r=Math.hypot(target.x,target.z)-.105;
      const h=target.y-.155,L1=.27,L2=.265,d=Math.hypot(r,h);
      if(r<.035||d>L1+L2-.008||d<Math.abs(L1-L2)+.008)return null;
      const shoulder=Math.atan2(h,r)+Math.acos(clamp((d*d+L1*L1-L2*L2)/(2*d*L1),-1,1));
      const elbow=-Math.acos(clamp((d*d-L1*L1-L2*L2)/(2*L1*L2),-1,1));
      return {yaw,shoulder,elbow,wrist:-(shoulder+elbow),grip:0};
    }
    reachTo(x,y,z,gesture="point",options={}){
      this.home();
      const reduced=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if(this.mode==="rover"){
        if(options.validated===false)return {ok:false,reason:"S6 path is blocked"};
        const path=Array.isArray(options.path)&&options.path.length>1?options.path:[this.start,[x,y]];
        let remaining=.20,points=[path[0]];
        for(let i=path.length-1;i>0;i--){
          const a=path[i-1],b=path[i],length=Math.hypot(b[0]-a[0],b[1]-a[1]);
          if(remaining<=length){
            const u=(length-remaining)/(length||1);
            points=path.slice(0,i);points.push([a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u]);break;
          }
          remaining-=length;
        }
        const length=points.slice(1).reduce((s,p,i)=>s+Math.hypot(p[0]-points[i][0],p[1]-points[i][1]),0);
        this.motion={kind:gesture,side:"rover",start:performance.now(),duration:reduced?1:Math.max(2800,length/.22*1000+1000),points,target:[x,y],gripped:false};
        return {ok:true,side:"rover",mode:gesture};
      }
      if(this.mode!=="arm")return {ok:false,reason:"Select a robot first"};
      const goal=this.solveArm(x,y,Math.max(z,.055));
      if(!goal)return {ok:false,reason:"Target is outside the mounted arm's reach"};
      const lift=gesture==="take"?this.solveArm(x,y,Math.max(z,.055)+.12):null;
      if(gesture==="take"&&!lift)return {ok:false,reason:"The arm cannot lift this target"};
      const from=this.pose(),closed={...goal,grip:1};
      this.motion={kind:gesture,side:"arm",start:performance.now(),duration:reduced?1:3900,from,goal,closed,lift:lift?{...lift,grip:1}:null,gripped:false};
      return {ok:true,side:"arm",mode:gesture};
    }
    update(now){
      const m=this.motion;if(!m)return;
      const t=clamp((now-m.start)/m.duration,0,1);
      if(m.side==="rover"){
        const drive=Math.min(1,t/.75),points=m.points;
        const segments=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
        const total=segments.reduce((a,b)=>a+b,0),distance=total*smooth(drive);
        let travelled=0,p=points[points.length-1],next=m.target;
        for(let i=0;i<segments.length;i++){
          if(travelled+segments[i]>=distance){const u=(distance-travelled)/(segments[i]||1);p=[finish(points[i][0],points[i+1][0],u),finish(points[i][1],points[i+1][1],u)];next=points[i+1];break;}
          travelled+=segments[i];
        }
        this.roverRoot.position.copy(M(...p));
        const face=drive<1?next:m.target;
        const v=M(face[0]-p[0],face[1]-p[1]);if(v.lengthSq()>1e-8)this.roverRoot.rotation.y=Math.atan2(-v.x,-v.z);
        if(m.kind==="take"&&t>.75){
          this.roverGripper.position.z=-.087-.036*smooth((t-.75)/.14);
          this.roverGripper.position.y=.053+.035*smooth((t-.9)/.1);
          this.applyRoverGrip(smooth((t-.85)/.15));
          if(t>.87)m.gripped=true;
        }
        for(const wheel of this.wheels)wheel.rotation.x+=.05;
        if(t>=1){if(m.kind==="take")this.held={side:"rover"};this.motion=null;}
      }else{
        const blend=(a,b,u)=>Object.fromEntries(Object.keys(a).map(k=>[k,finish(a[k],b[k],u)]));
        if(m.kind==="take"){
          if(t<.43)this.applyPose(blend(m.from,m.goal,t/.43));
          else if(t<.58)this.applyPose(blend(m.goal,m.closed,(t-.43)/.15));
          else{m.gripped=true;this.applyPose(blend(m.closed,m.lift,(t-.58)/.42));}
          if(t>=1){this.applyPose(m.lift);this.held={side:"arm"};this.motion=null;}
        }else{
          if(t<.45)this.applyPose(blend(m.from,m.goal,t/.45));
          else if(t<.68)this.applyPose(m.goal);
          else this.applyPose(blend(m.goal,m.from,(t-.68)/.32));
          if(t>=1){this.applyPose(m.from);this.motion=null;}
        }
      }
    }
  }
  window.TableRobots=TableRobots;
})();
