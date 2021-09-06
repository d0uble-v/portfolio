using UnityEngine;

namespace Sourcery.Stats
{
    [System.Serializable]
    public class FloorStat : Stat
    {
        [SerializeReference] protected StatValue minValue;
        public virtual StatValue MinValue => minValue;


        [SerializeReference] protected SimpleValue currentValue;
        public virtual SimpleValue CurrentValue => currentValue;


        public FloorStat(string name, StatValue min, SimpleValue current, StatSystem statSystem) : base(name, statSystem)
        {
            minValue = min;
            currentValue = current;
        }


        public virtual void InitConstraints()
        {
            // Apply constraints
            CurrentValue.AddConstraint(new FloorConstraint(MinValue, CurrentValue));
        }
    }
}