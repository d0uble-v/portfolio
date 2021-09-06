using UnityEngine;


namespace Sourcery.Stats
{
    public class FloorConstraint : IConstraint
    {
        protected StatValue min;
        protected SimpleValue current;

        public FloorConstraint(StatValue minValue, SimpleValue currentValue)
        {
            min = minValue;
            current = currentValue;

            // Subscribe to changed event
            min.Changed += RecalculateCurrentValue;
        }

        public virtual float Apply(float amount)
        {
            return Mathf.Max(min.Amount, amount);
        }

        protected virtual void RecalculateCurrentValue(StatValue value)
        {
            current.RecalculateAmount();
        }
    }
}
