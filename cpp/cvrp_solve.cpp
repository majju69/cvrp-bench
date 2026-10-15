#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

using namespace std;
using Route=vector<int>;
using Routes=vector<Route>;

struct Instance
{
    string name;
    int capacity=0;
    int n=0;
    vector<pair<double,double>> xy;
    vector<int> demand;
    vector<vector<int>> d;
};

int euc_2d(pair<double,double> a,pair<double,double> b)
{
    return (int)(sqrt((a.first-b.first)*(a.first-b.first)+(a.second-b.second)*(a.second-b.second))+0.5);
}

string trim(const string &s)
{
    auto first=s.find_first_not_of(" \t\r");
    if(first==string::npos)
    {
        return "";
    }
    auto last=s.find_last_not_of(" \t\r");
    return s.substr(first,last-first+1);
}

Instance read_vrp(const string &path)
{
    ifstream in(path);
    if(!in)
    {
        throw runtime_error("cannot open "+path);
    }
    Instance inst;
    map<int,pair<double,double>> coords;
    map<int,int> dem;
    string line,section;
    while(getline(in,line))
    {
        line=trim(line);
        if(line.empty()||line=="EOF")
        {
            continue;
        }
        if(line.find("_SECTION")!=string::npos)
        {
            section=line;
            continue;
        }
        auto colon=line.find(':');
        if(section.empty()&&colon!=string::npos)
        {
            string key=line.substr(0,colon),val=line.substr(colon+1);
            key=trim(key);
            val=trim(val);
            if(key=="NAME")
            {
                inst.name=val;
            }
            else if(key=="CAPACITY")
            {
                inst.capacity=stoi(val);
            }
            else if(key=="EDGE_WEIGHT_TYPE")
            {
                if(val!="EUC_2D")
                {
                    throw runtime_error("only EUC_2D is supported");
                }
            }
            else
            {
                continue;
            }
        }
        istringstream ss(line);
        if(section=="NODE_COORD_SECTION")
        {
            int id=0;
            double x=0,y=0;
            ss>>id>>x>>y;
            coords[id]={x,y};
        }
        else if(section=="DEMAND_SECTION")
        {
            int id=0,d=0;
            ss>>id>>d;
            dem[id]=d;
        }
        else if(section=="DEPOT_SECTION")
        {
            int id=-1;
            ss>>id;
            if(id!=-1&&id!=1)
            {
                throw runtime_error("depot must be node 1");
            }
        }
    }
    for(auto &[id,p]:coords)
    {
        inst.xy.push_back(p);
        inst.demand.emplace_back(dem[id]);
    }
    inst.n=(int)inst.xy.size();
    inst.d.assign(inst.n,vector<int>(inst.n));
    for(int i=0;i<inst.n;++i)
    {
        for(int j=0;j<inst.n;++j)
        {
            inst.d[i][j]=euc_2d(inst.xy[i],inst.xy[j]);
        }
    }
    return inst;
}

int route_cost(const Instance &inst,const Route &route)
{
    if(route.empty())
    {
        return 0;
    }
    int cost=inst.d[0][route[0]]+inst.d[route.back()][0];
    for(size_t i=0;i<route.size()-1;++i)
    {
        cost+=inst.d[route[i]][route[i+1]];
    }
    return cost;
}

int total_cost(const Instance &inst,const Routes &routes)
{
    int cost=0;
    for(const auto &route:routes)
    {
        cost+=route_cost(inst,route);
    }
    return cost;
}

int route_load(const Instance &inst,const Route &route)
{
    int load=0;
    for(int i:route)
    {
        load+=inst.demand[i];
    }
    return load;
}

Routes nearest_neighbor(const Instance &inst)
{
    vector<bool> vis(inst.n,0);
    int left=inst.n-1;
    Routes routes;
    while(left>0)
    {
        Route route;
        int load=0,cur=0;
        while(1)
        {
            int nxt=-1;
            for(int i=1;i<inst.n;++i)
            {
                if(!vis[i]&&load+inst.demand[i]<=inst.capacity&&(nxt==-1||inst.d[cur][i]<inst.d[cur][nxt]))
                {
                    nxt=i;
                }
            }
            if(nxt==-1)
            {
                break;
            }
            route.emplace_back(nxt);
            vis[nxt]=true;
            load+=inst.demand[nxt];
            cur=nxt;
            left--;
        }
        routes.emplace_back(route);
    }
    return routes;
}

Routes clarke_wright(const Instance &inst)
{
    vector<Route> pool(inst.n);
    vector<int> rid(inst.n),load(inst.n);
    for(int i=1;i<inst.n;++i)
    {
        pool[i]={i};
        rid[i]=i;
        load[i]=inst.demand[i];
    }
    vector<tuple<int,int,int>> savings;
    for(int i=1;i<inst.n;++i)
    {
        for(int j=i+1;j<inst.n;++j)
        {
            savings.emplace_back(inst.d[0][i]+inst.d[0][j]-inst.d[i][j],i,j);
        }
    }
    sort(savings.rbegin(),savings.rend());
    for(auto [s,i,j]:savings)
    {
        if(s<=0)
        {
            break;
        }
        int a=rid[i],b=rid[j];
        if(a==b||load[a]+load[b]>inst.capacity)
        {
            continue;
        }
        Route &ri=pool[a],&rj=pool[b];
        Route merged;
        if(ri.back()==i&&rj.front()==j)
        {
            merged=ri;
            merged.insert(merged.end(),rj.begin(),rj.end());
        }
        else if(ri.front()==i&&rj.back()==j)
        {
            merged=rj;
            merged.insert(merged.end(),ri.begin(),ri.end());
        }
        else if(ri.front()==i&&rj.front()==j)
        {
            merged.assign(ri.rbegin(),ri.rend());
            merged.insert(merged.end(),rj.begin(),rj.end());
        }
        else if(ri.back()==i&&rj.back()==j)
        {
            merged=ri;
            merged.insert(merged.end(),rj.rbegin(),rj.rend());
        }
        else
        {
            continue;
        }
        int id=(int)pool.size();
        pool.emplace_back(merged);
        load.emplace_back(load[a]+load[b]);
        for(int c:pool[id])
        {
            rid[c]=id;
        }
        pool[a].clear();
        pool[b].clear();
    }
    Routes out;
    vector<bool> vis(pool.size(),0);
    for(int i=1;i<inst.n;++i)
    {
        if(!vis[rid[i]])
        {
            out.emplace_back(pool[rid[i]]);
            vis[rid[i]]=1;
        }
    }
    return out;
}

Route two_opt(const Instance &inst,const Route &route)
{
    Route r;
    r.reserve(route.size()+2);
    r.emplace_back(0);
    r.insert(r.end(),route.begin(),route.end());
    r.emplace_back(0);
    const auto &d=inst.d;
    bool improved=1;
    while(improved)
    {
        improved=0;
        for(size_t i=1;i<r.size()-2;++i)
        {
            for(size_t j=i+1;j<r.size()-1;++j)
            {
                int a=r[i-1],b=r[i],c=r[j],e=r[j+1];
                if(d[a][c]+d[b][e]<d[a][b]+d[c][e])
                {
                    reverse(r.begin()+i,r.begin()+j+1);
                    improved=1;
                }
            }
        }
    }
    return Route(r.begin()+1,r.end()-1);
}

struct Move
{
    int gain=0,a=-1,i=-1,b=-1,j=-1;
};

Move best_relocate(const Instance &inst,const Routes &routes)
{
    const auto &d=inst.d;
    vector<int> loads;
    for(auto &route:routes)
    {
        loads.emplace_back(route_load(inst,route));
    }
    Move best;
    for(int a=0;a<(int)routes.size();++a)
    {
        const auto &ra=routes[a];
        for(int i=0;i<(int)ra.size();++i)
        {
            int c=ra[i];
            int prev=((i>0)?ra[i-1]:0),nxt=((i+1<(int)ra.size())?ra[i+1]:0);
            int remove_gain=d[prev][c]+d[c][nxt]-d[prev][nxt];
            for(int b=0;b<(int)routes.size();++b)
            {
                const auto &rb=routes[b];
                if(b!=a&&loads[b]+inst.demand[c]>inst.capacity)
                {
                    continue;
                }
                for(int pos=0;pos<=(int)rb.size();++pos)
                {
                    if(b==a&&(pos==i||pos==i+1))
                    {
                        continue;
                    }
                    int p=((pos>0)?rb[pos-1]:0),q=((pos<(int)rb.size())?rb[pos]:0);
                    if(b==a&&(p==c||q==c))
                    {
                        continue;
                    }
                    int gain=remove_gain-(d[p][c]+d[c][q]-d[p][q]);
                    if(gain>best.gain)
                    {
                        best={gain,a,i,b,pos};
                    }
                }
            }
        }
    }
    return best;
}

Routes apply_relocate(Routes routes,const Move &m)
{
    int c=routes[m.a][m.i];
    routes[m.a].erase(routes[m.a].begin()+m.i);
    int pos=((m.a==m.b&&m.j>m.i)?m.j-1:m.j);
    routes[m.b].insert(routes[m.b].begin()+pos,c);
    Routes out;
    for(auto &route:routes)
    {
        if(!route.empty())
        {
            out.emplace_back(route);
        }
    }
    return out;
}

Move best_swap(const Instance &inst,const Routes &routes)
{
    const auto &d=inst.d;
    const auto &dem=inst.demand;
    vector<int> loads;
    for(auto &route:routes)
    {
        loads.emplace_back(route_load(inst,route));
    }
    auto nb=[](const Route &r,int i)
    {
        return pair{(i>0)?r[i-1]:0,(i+1<(int)r.size())?r[i+1]:0};
    };
    Move best;
    for(int a=0;a<(int)routes.size();++a)
    {
        for(int b=a+1;b<(int)routes.size();++b)
        {
            for(int i=0;i<(int)routes[a].size();++i)
            {
                int x=routes[a][i];
                auto [pa,na]=nb(routes[a],i);
                for(int j=0;j<(int)routes[b].size();++j)
                {
                    int y=routes[b][j];
                    if(loads[a]-dem[x]+dem[y]>inst.capacity||loads[b]-dem[y]+dem[x]>inst.capacity)
                    {
                        continue;
                    }
                    auto [pb,nbb]=nb(routes[b],j);
                    int gain=(d[pa][x]+d[x][na]+d[pb][y]+d[y][nbb])-(d[pa][y]+d[y][na]+d[pb][x]+d[x][nbb]);
                    if(gain>best.gain)
                    {
                        best={gain,a,i,b,j};
                    }
                }
            }
        }
    }
    return best;
}

Routes local_search(const Instance &inst,const Routes &routes)
{
    Routes cur;
    for(auto &route:routes)
    {
        if(!route.empty())
        {
            cur.emplace_back(two_opt(inst,route));
        }
    }
    while(1)
    {
        Move m1=best_relocate(inst,cur),m2=best_swap(inst,cur);
        if(m1.gain<=0&&m2.gain<=0)
        {
            return cur;
        }
        if(m1.gain>=m2.gain)
        {
            cur=apply_relocate(cur,m1);
        }
        else
        {
            swap(cur[m2.a][m2.i],cur[m2.b][m2.j]);
        }
        for(auto &route:cur)
        {
            route=two_opt(inst,route);
        }
    }   
}

pair<Routes,vector<int>> ruin(const Instance &inst,const Routes &routes,int k,mt19937 &rng)
{
    int seed=uniform_int_distribution<int>(1,inst.n-1)(rng);
    vector<int> cust(inst.n-1);
    iota(cust.begin(),cust.end(),1);
    stable_sort(cust.begin(),cust.end(),[&](int a,int b){return inst.d[seed][a]<inst.d[seed][b];});
    vector<int> removed(cust.begin(),cust.begin()+min(k,inst.n-1));
    vector<bool> gone(inst.n,0);
    for(int c:removed)
    {
        gone[c]=1;
    }
    Routes kept;
    for(auto &route:routes)
    {
        Route nr;
        for(int c:route)
        {
            if(!gone[c])
            {
                nr.emplace_back(c);
            }
        }
        if(!nr.empty())
        {
            kept.emplace_back(nr);
        }
    }
    return {kept,removed};
}

Routes recreate(const Instance &inst,Routes routes,vector<int> &removed,mt19937 &rng)
{
    const auto &d=inst.d;
    vector<int> loads;
    for(auto &route:routes)
    {
        loads.emplace_back(route_load(inst,route));
    }
    shuffle(removed.begin(),removed.end(),rng);
    for(int c:removed)
    {
        int best_delta=INT32_MAX,bk=-1,bpos=-1;
        for(size_t k=0;k<routes.size();++k)
        {
            if(loads[k]+inst.demand[c]>inst.capacity)
            {
                continue;
            }
            for(int pos=0;pos<=(int)routes[k].size();++pos)
            {
                int p=((pos>0)?routes[k][pos-1]:0),q=((pos<(int)routes[k].size())?routes[k][pos]:0);
                int delta=d[p][c]+d[c][q]-d[p][q];
                if(delta<best_delta)
                {
                    best_delta=delta;
                    bk=k;
                    bpos=pos;
                }
            }
        }
        if(bk==-1)
        {
            routes.emplace_back(Route{c});
            loads.emplace_back(inst.demand[c]);
        }
        else
        {
            routes[bk].insert(routes[bk].begin()+bpos,c);
            loads[bk]+=inst.demand[c];
        }
    }
    return routes;
}

Routes lns(const Instance &inst,double time_limit,unsigned seed,long long &iters)
{
    mt19937 rng(seed);
    uniform_real_distribution<double> unif(0.0,1.0);
    Routes cur=local_search(inst,clarke_wright(inst));
    int cur_cost=total_cost(inst,cur);
    Routes best=cur;
    int best_cost=cur_cost;
    double temp0=0.3*cur_cost/inst.n;
    auto start=chrono::steady_clock::now();
    iters=0;
    while(1)
    {
        double elapsed=chrono::duration<double>(chrono::steady_clock::now()-start).count();
        if(elapsed>=time_limit)
        {
            break;
        }
        double temp=temp0*(1.0-elapsed/time_limit)+1e-9;
        int k=uniform_int_distribution<int>(3,max(4,inst.n/6))(rng);
        auto [partial,removed]=ruin(inst,cur,k,rng);
        Routes cand=local_search(inst,recreate(inst,partial,removed,rng));
        int cand_cost=total_cost(inst,cand);
        if(cand_cost<cur_cost||(unif(rng)<exp((cur_cost-cand_cost)/temp)))
        {
            cur=cand;
            cur_cost=cand_cost;
            if(cur_cost<best_cost)
            {
                best=cur;
                best_cost=cur_cost;
            }
        }
        iters++;
    }
    return best;
}

int main(int argc,char **argv)
{
    if(argc<3)
    {
        cerr<<"usage: cvrp_solve <file.vrp> <nn|cw|ls|lns> [seconds=10] [seed=0]\n";
        return 2;
    }
    try
    {
        Instance inst=read_vrp(argv[1]);
        string method=argv[2];
        double seconds=((argc>3)?stod(argv[3]):10.0);
        unsigned seed=((argc>4)?(unsigned)stoul(argv[4]):0u);
        long long iters=0;
        auto t0=chrono::steady_clock::now();
        Routes R;
        if(method=="nn")
        {
            R=nearest_neighbor(inst);
        }
        else if(method=="cw")
        {
            R=clarke_wright(inst);
        }
        else if(method=="ls")
        {
            R=local_search(inst,clarke_wright(inst));
        }
        else if(method=="lns")
        {
            R=lns(inst,seconds,seed,iters);
        }
        else
        {
            cerr<<"unknown method: "<<method<<'\n';
            return 2;
        }
        double secs=chrono::duration<double>(chrono::steady_clock::now()-t0).count();
        for(auto &r:R)
        {
            cout<<"route";
            for(int i:r)
            {
                cout<<' '<<i;
            }
            cout<<'\n';
        }
        cout<<"cost "<<total_cost(inst,R)<<'\n';
        cout<<"iterations "<<iters<<'\n';
        cout<<"seconds "<<fixed;
        cout.precision(3);
        cout<<secs<<'\n';
    }
    catch(const exception &e)
    {
        cerr<<"error: "<<e.what()<<'\n';
        return 1;
    }
    return 0;
}