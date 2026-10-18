// DronSwarm · Falla de motor física para Gazebo (gz-sim 7).
//
// El plugin de motores de gz-sim no permite apagar un motor, y la inyección de fallas de PX4 1.15 solo altera la
// telemetría del ESC (el motor simulado sigue empujando). Este sistema de modelo anula el empuje y el par de
// arrastre de un rotor con la misma fórmula que usa gz::sim::systems::MulticopterMotorModel, así que para el
// autopiloto el motor deja de existir: es lo que pasa con un ESC quemado o una hélice rota.
//
// En el model.sdf (lo agrega tools/gen_sdf.py con los parámetros de cada rotor):
//   <plugin filename="dronswarm-motor-failure-system" name="dronswarm::MotorFailureSystem">
//     <motorConstant>3.37e-4</motorConstant> <momentConstant>0.041</momentConstant>
//     <rotorVelocitySlowdownSim>10</rotorVelocitySlowdownSim>
//     <rotor link="rotor_0" joint="rotor_0_joint" direction="ccw"/> ...
//   </plugin>
//
// Falla:     gz topic -t /model/ds_d_0/motor_failure -m gz.msgs.Int32 -p "data: 2"    (apaga el motor 2)
// Reparar:   gz topic -t /model/ds_d_0/motor_failure -m gz.msgs.Int32 -p "data: -1"

#include <gz/math/Pose3.hh>
#include <gz/math/Vector3.hh>
#include <gz/msgs/int32.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/transport/Node.hh>

#include <algorithm>
#include <atomic>
#include <string>
#include <vector>

namespace dronswarm
{
using namespace gz;
using namespace gz::sim;

struct Rotor
{
  std::string link, joint;
  double direction{1.0};  // ccw = +1, cw = -1 (como el plugin de motores)
  Entity linkEnt{kNullEntity}, jointEnt{kNullEntity};
};

class MotorFailureSystem : public System, public ISystemConfigure, public ISystemPreUpdate
{
public:
  void Configure(const Entity &_entity, const std::shared_ptr<const sdf::Element> &_sdf, EntityComponentManager &_ecm,
                 EventManager &) override
  {
    this->model = Model(_entity);
    auto sdf = _sdf->Clone();
    this->motorConstant = sdf->Get<double>("motorConstant", this->motorConstant).first;
    this->momentConstant = sdf->Get<double>("momentConstant", this->momentConstant).first;
    this->slowdown = sdf->Get<double>("rotorVelocitySlowdownSim", this->slowdown).first;
    for (auto e = sdf->GetElement("rotor"); e; e = e->GetNextElement("rotor"))
    {
      Rotor r;
      r.link = e->Get<std::string>("link");
      r.joint = e->Get<std::string>("joint");
      r.direction = e->Get<std::string>("direction") == "cw" ? -1.0 : 1.0;
      this->rotors.push_back(r);
    }
    const std::string name = this->model.Name(_ecm);
    const std::string topic = "/model/" + name + "/motor_failure";
    this->node.Subscribe(topic, &MotorFailureSystem::OnFailure, this);
    gzmsg << "[MotorFailure] " << name << ": " << this->rotors.size() << " rotores, tópico " << topic << "\n";
  }

  void PreUpdate(const UpdateInfo &_info, EntityComponentManager &_ecm) override
  {
    const int k = this->failed.load();
    if (_info.paused || k < 0 || k >= static_cast<int>(this->rotors.size())) return;
    Rotor &r = this->rotors[k];
    if (r.linkEnt == kNullEntity)
    {
      r.linkEnt = this->model.LinkByName(_ecm, r.link);
      r.jointEnt = this->model.JointByName(_ecm, r.joint);
      this->baseEnt = this->model.LinkByName(_ecm, "base_link");
      if (r.linkEnt == kNullEntity || r.jointEnt == kNullEntity) return;
      Link(r.linkEnt).EnableVelocityChecks(_ecm, true);
    }
    const auto *jv = _ecm.Component<components::JointVelocity>(r.jointEnt);
    if (!jv || jv->Data().empty()) return;
    Link link(r.linkEnt);
    const auto pose = link.WorldPose(_ecm);
    const auto vel = link.WorldLinearVelocity(_ecm);
    if (!pose || !vel) return;
    // Igual que MulticopterMotorModel: empuje = k·(ω·slowdown)² escalado por el viento perpendicular al eje
    const double w = jv->Data()[0] * this->slowdown;
    double thrust = this->motorConstant * w * w;
    const math::Vector3d axis = pose->Rot().RotateVector(math::Vector3d::UnitZ);
    const math::Vector3d vPerp = *vel - vel->Dot(axis) * axis;
    thrust *= std::clamp(1.0 - vPerp.Length() / 25.0, 0.0, 1.0);
    link.AddWorldForce(_ecm, -thrust * axis);                       // anula el empuje
    if (this->baseEnt != kNullEntity)                               // anula el par de arrastre sobre el cuerpo
    {
      const math::Vector3d drag = -r.direction * thrust * this->momentConstant * axis;
      Link(this->baseEnt).AddWorldWrench(_ecm, math::Vector3d::Zero, -drag);
    }
  }

private:
  void OnFailure(const msgs::Int32 &_msg)
  {
    this->failed.store(_msg.data());
    if (_msg.data() >= 0)
      gzwarn << "[MotorFailure] motor " << _msg.data() << " APAGADO\n";
    else
      gzmsg << "[MotorFailure] motores restablecidos\n";
  }

  Model model{kNullEntity};
  Entity baseEnt{kNullEntity};
  std::vector<Rotor> rotors;
  double motorConstant{8.54858e-06};
  double momentConstant{0.016};
  double slowdown{10.0};
  std::atomic<int> failed{-1};
  transport::Node node;
};
}  // namespace dronswarm

GZ_ADD_PLUGIN(dronswarm::MotorFailureSystem, gz::sim::System, dronswarm::MotorFailureSystem::ISystemConfigure,
              dronswarm::MotorFailureSystem::ISystemPreUpdate)
GZ_ADD_PLUGIN_ALIAS(dronswarm::MotorFailureSystem, "dronswarm::MotorFailureSystem")
