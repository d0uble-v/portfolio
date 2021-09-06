using UnityEngine;

namespace Sourcery.Stats
{
    [System.Serializable]
    public class RangeStat : FloorStat
    {
        [SerializeReference] protected StatValue maxValue;
        public virtual StatValue MaxValue => maxValue;


        public RangeStat(string name, StatValue min, SimpleValue current, StatValue max, StatSystem statSystem) 
            : base(name, min, current, statSystem)
        {
            maxValue = max;
        }


        public override void InitConstraints()
        {
            // Apply constraints
            CurrentValue.AddConstraint(new RangeConstraint(MinValue, CurrentValue, MaxValue));
        }
    }
}