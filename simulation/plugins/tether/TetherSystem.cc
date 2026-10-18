// DronSwarm · Sistema de cuerdas para Gazebo (gz-sim 7).
//
// Modela cada cuerda como un resorte-amortiguador que SOLO TIRA (una cuerda no empuja): entre un punto de un link
// (gancho del dron) y otro (anclaje de la caja). Las fuerzas se aplican en cada paso de física, sin uniones entre
// modelos, que es lo que hace inestable al solver DART cuando se sueldan cuerpos de masas muy distintas.
// También publica las cuerdas como líneas (marcadores) para verlas en la ventana de Gazebo.
//
// Uso en el <world>:
//   <plugin filename="dronswarm-tether-system" name="dronswarm::TetherSystem">
//     <stiffness>4000</stiffness> <damping>80</damping>
//     <tether><a model="ds_d_coop_0" link="base_link" offset="0 0 -0.1"/>
//             <b model="coop_payload" link="box" offset="0 0.15 0.15"/> <length>3.2</length></tether>
//   </plugin>
//
// Liberación: publicar en /tether/<índice>/release (gz.msgs.Boolean, data: true) suelta esa cuerda; sirve para
// simular el gancho de entrega:  gz topic -t /tether/0/release -m gz.msgs.Boolean -p "data: true"

#include <gz/math/Pose3.hh>
#include <gz/math/Vector3.hh>
#include <gz/msgs/boolean.pb.h>
#include <gz/msgs/marker.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>
#include <gz/transport/Node.hh>

#include <atomic>
#include <chrono>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace dronswarm
{
using namespace gz;
using namespace gz::sim;

struct EndPoint
{
  std::string model, link;
  math::Vector3d offset;
  Entity entity{kNullEntity};
};

struct Tether
{
  EndPoint a, b;
  double length{1.0};
  double tension{0.0};
  std::shared_ptr<std::atomic<bool>> released{std::make_shared<std::atomic<bool>>(false)};
};

class TetherSystem : public System, public ISystemConfigure, public ISystemPreUpdate
{
public:
  void Configure(const Entity &, const std::shared_ptr<const sdf::Element> &_sdf, EntityComponentManager &,
                 EventManager &) override
  {
    auto sdf = _sdf->Clone();
    if (sdf->HasElement("stiffness")) this->stiffness = sdf->Get<double>("stiffness");
    if (sdf->HasElement("damping")) this->damping = sdf->Get<double>("damping");
    for (auto e = sdf->GetElement("tether"); e; e = e->GetNextElement("tether"))
    {
      Tether t;
      t.a = this->ParseEnd(e->GetElement("a"));
      t.b = this->ParseEnd(e->GetElement("b"));
      t.length = e->Get<double>("length");
      const std::string topic = "/tether/" + std::to_string(this->tethers.size()) + "/release";
      auto flag = t.released;
      this->node.Subscribe(topic, std::function<void(const msgs::Boolean &)>(
          [flag, topic](const msgs::Boolean &_msg)
          {
            flag->store(_msg.data());
            gzmsg << "[TetherSystem] " << topic << (_msg.data() ? ": cuerda soltada\n" : ": cuerda enganchada\n");
          }));
      this->tethers.push_back(t);
    }
    gzmsg << "[TetherSystem] " << this->tethers.size() << " cuerdas, k=" << this->stiffness
          << " N/m, c=" << this->damping << " N·s/m\n";
  }

  void PreUpdate(const UpdateInfo &_info, EntityComponentManager &_ecm) override
  {
    if (_info.paused) return;
    std::vector<std::pair<math::Vector3d, math::Vector3d>> lines;
    for (auto &t : this->tethers)
    {
      if (t.released->load()) continue;                            // cuerda soltada: sin fuerza ni línea
      if (!this->Resolve(t.a, _ecm) || !this->Resolve(t.b, _ecm)) continue;
      Link la(t.a.entity), lb(t.b.entity);
      auto pa = la.WorldPose(_ecm), pb = lb.WorldPose(_ecm);
      auto va = la.WorldLinearVelocity(_ecm, t.a.offset), vb = lb.WorldLinearVelocity(_ecm, t.b.offset);
      if (!pa || !pb || !va || !vb) continue;
      const math::Vector3d xa = pa->Pos() + pa->Rot().RotateVector(t.a.offset);
      const math::Vector3d xb = pb->Pos() + pb->Rot().RotateVector(t.b.offset);
      lines.emplace_back(xa, xb);
      const math::Vector3d d = xb - xa;
      const double dist = d.Length();
      t.tension = 0.0;
      if (dist <= t.length || dist < 1e-6) continue;            // cuerda floja: no hay fuerza
      const math::Vector3d dir = d / dist;
      double tension = this->stiffness * (dist - t.length) + this->damping * (*vb - *va).Dot(dir);
      if (tension <= 0.0) continue;                              // una cuerda no empuja
      t.tension = tension;
      la.AddWorldForce(_ecm, dir * tension, t.a.offset);
      lb.AddWorldForce(_ecm, -dir * tension, t.b.offset);
    }
    this->PublishMarkers(_info, lines);
  }

private:
  EndPoint ParseEnd(const sdf::ElementPtr &_e)
  {
    EndPoint p;
    p.model = _e->Get<std::string>("model");
    p.link = _e->Get<std::string>("link");
    if (_e->HasAttribute("offset"))
    {
      std::istringstream ss(_e->GetAttribute("offset")->GetAsString());
      double x, y, z;
      ss >> x >> y >> z;
      p.offset.Set(x, y, z);
    }
    return p;
  }

  bool Resolve(EndPoint &_p, EntityComponentManager &_ecm)
  {
    if (_p.entity != kNullEntity) return true;
    const Entity m = _ecm.EntityByComponents(components::Model(), components::Name(_p.model));
    if (m == kNullEntity) return false;                          // el dron todavía no aparece
    const Entity l = Model(m).LinkByName(_ecm, _p.link);
    if (l == kNullEntity) return false;
    Link(l).EnableVelocityChecks(_ecm, true);
    _p.entity = l;
    gzmsg << "[TetherSystem] enganchado " << _p.model << "::" << _p.link << "\n";
    return true;
  }

  void PublishMarkers(const UpdateInfo &_info, const std::vector<std::pair<math::Vector3d, math::Vector3d>> &_lines)
  {
    const auto now = std::chrono::duration<double>(_info.simTime).count();
    if (now - this->lastMarker < 0.1) return;                      // 10 Hz basta para ver
    this->lastMarker = now;
    msgs::Marker marker;
    marker.set_ns("dronswarm_tethers");
    marker.set_id(1);
    if (_lines.empty())                                            // todas soltadas: borrar la línea dibujada
    {
      if (!this->markerShown) return;
      marker.set_action(msgs::Marker::DELETE_MARKER);
      this->node.Request("/marker", marker);
      this->markerShown = false;
      return;
    }
    this->markerShown = true;
    marker.set_action(msgs::Marker::ADD_MODIFY);
    marker.set_type(msgs::Marker::LINE_LIST);
    for (const auto &[a, b] : _lines)
    {
      msgs::Set(marker.add_point(), a);
      msgs::Set(marker.add_point(), b);
    }
    auto *mat = marker.mutable_material();
    msgs::Set(mat->mutable_ambient(), math::Color(0.05, 0.05, 0.05, 1));
    msgs::Set(mat->mutable_diffuse(), math::Color(0.05, 0.05, 0.05, 1));
    this->node.Request("/marker", marker);
  }

  std::vector<Tether> tethers;
  double stiffness{4000.0};
  double damping{80.0};
  double lastMarker{-1.0};
  bool markerShown{false};
  transport::Node node;
};
}  // namespace dronswarm

GZ_ADD_PLUGIN(dronswarm::TetherSystem, gz::sim::System, dronswarm::TetherSystem::ISystemConfigure,
              dronswarm::TetherSystem::ISystemPreUpdate)
GZ_ADD_PLUGIN_ALIAS(dronswarm::TetherSystem, "dronswarm::TetherSystem")
