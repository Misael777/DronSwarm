// DronSwarm · Monitor de seguridad del enjambre para Gazebo (gz-sim 7).
//
// Con la posición REAL de cada dron (la del simulador, no la que estima PX4) registra a 10 Hz:
//   - la trayectoria de cada dron,
//   - la separación mínima entre cada par (centro a centro) y contra cada obstáculo (cilindro vertical),
//   - los contactos: pares a menos de la suma de sus radios (puntas de hélice tocándose) = colisión.
// Es el árbitro del criterio "0 colisiones en 20 corridas": no depende del código que se está probando.
//
//   <plugin filename="dronswarm-swarm-monitor-system" name="dronswarm::SwarmMonitorSystem">
//     <output>/ruta/monitor.csv</output>            (o la variable de entorno DRONSWARM_MONITOR_CSV)
//     <vehicle prefix="ds_i" radius="0.55"/> <vehicle prefix="ds_d" radius="1.05"/>
//     <obstacle name="torre" x="0" y="32" radius="1.0" height="25"/>
//   </plugin>
//
// CSV: t,model,x,y,z  y filas especiales  t,#pair,a|b,dist,0  /  t,#obst,model|obst,clearance,0  /  t,#contact,...

#include <gz/math/Pose3.hh>
#include <gz/plugin/Register.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/Pose.hh>

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <set>
#include <string>
#include <vector>

namespace dronswarm
{
using namespace gz;
using namespace gz::sim;

struct VehicleClass
{
  std::string prefix;
  double radius;
};

struct Cylinder
{
  std::string name;
  double x, y, radius, height;
};

class SwarmMonitorSystem : public System, public ISystemConfigure, public ISystemPostUpdate
{
public:
  void Configure(const Entity &, const std::shared_ptr<const sdf::Element> &_sdf, EntityComponentManager &,
                 EventManager &) override
  {
    auto sdf = _sdf->Clone();
    std::string path = sdf->Get<std::string>("output", "").first;
    if (const char *env = std::getenv("DRONSWARM_MONITOR_CSV"); env && *env) path = env;
    for (auto e = sdf->GetElement("vehicle"); e; e = e->GetNextElement("vehicle"))
      this->classes.push_back({e->Get<std::string>("prefix"), e->Get<double>("radius")});
    for (auto e = sdf->GetElement("obstacle"); e; e = e->GetNextElement("obstacle"))
      this->obstacles.push_back({e->Get<std::string>("name"), e->Get<double>("x"), e->Get<double>("y"),
                                 e->Get<double>("radius"), e->Get<double>("height")});
    if (!path.empty())
    {
      this->out.open(path);
      this->out << "t,model,x,y,z\n";
    }
    gzmsg << "[SwarmMonitor] " << this->classes.size() << " tipos de dron, " << this->obstacles.size()
          << " obstáculos → " << (path.empty() ? "(sin archivo)" : path) << "\n";
  }

  void PostUpdate(const UpdateInfo &_info, const EntityComponentManager &_ecm) override
  {
    if (_info.paused || !this->out.is_open()) return;
    const double t = std::chrono::duration<double>(_info.simTime).count();
    if (t - this->last < 0.1) return;
    this->last = t;

    struct V { std::string name; math::Vector3d p; double r; };
    std::vector<V> vs;
    _ecm.Each<components::Model, components::Name, components::Pose>(
        [&](const Entity &, const components::Model *, const components::Name *_name, const components::Pose *_pose)
        {
          for (const auto &c : this->classes)
            if (_name->Data().rfind(c.prefix, 0) == 0)
            {
              vs.push_back({_name->Data(), _pose->Data().Pos(), c.radius});
              break;
            }
          return true;
        });
    for (const auto &v : vs)
      this->out << t << "," << v.name << "," << v.p.X() << "," << v.p.Y() << "," << v.p.Z() << "\n";
    for (size_t a = 0; a < vs.size(); ++a)
    {
      if (vs[a].p.Z() < 0.6) continue;                        // en el suelo (antes de despegar / ya aterrizado)
      for (size_t b = a + 1; b < vs.size(); ++b)
      {
        if (vs[b].p.Z() < 0.6) continue;
        const double d = vs[a].p.Distance(vs[b].p);
        this->out << t << ",#pair," << vs[a].name << "|" << vs[b].name << "," << d << ",0\n";
        this->Contact(t, vs[a].name + "|" + vs[b].name, d < vs[a].r + vs[b].r);
      }
      for (const auto &o : this->obstacles)
      {
        if (vs[a].p.Z() > o.height + vs[a].r) continue;
        const double c = std::hypot(vs[a].p.X() - o.x, vs[a].p.Y() - o.y) - o.radius - vs[a].r;
        this->out << t << ",#obst," << vs[a].name << "|" << o.name << "," << c << ",0\n";
        this->Contact(t, vs[a].name + "|" + o.name, c < 0);
      }
    }
    this->out.flush();
  }

private:
  void Contact(double t, const std::string &key, bool touching)
  {
    if (touching && !this->contacts.count(key))
    {
      this->contacts.insert(key);
      this->out << t << ",#contact," << key << ",0,0\n";
      gzwarn << "[SwarmMonitor] COLISIÓN " << key << " en t=" << t << " s\n";
    }
    else if (!touching)
      this->contacts.erase(key);
  }

  std::vector<VehicleClass> classes;
  std::vector<Cylinder> obstacles;
  std::set<std::string> contacts;
  std::ofstream out;
  double last{-1.0};
};
}  // namespace dronswarm

GZ_ADD_PLUGIN(dronswarm::SwarmMonitorSystem, gz::sim::System, dronswarm::SwarmMonitorSystem::ISystemConfigure,
              dronswarm::SwarmMonitorSystem::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(dronswarm::SwarmMonitorSystem, "dronswarm::SwarmMonitorSystem")
