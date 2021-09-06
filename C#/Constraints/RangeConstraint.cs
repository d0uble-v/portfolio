using UnityEngine;


namespace Sourcery.Stats
{
    public class RangeConstraint : FloorConstraint
    {
        protected StatValue max;

        public RangeConstraint(StatValue minValue, SimpleValue currentValue, StatValue maxValue) : base(minValue, currentValue)
        {
            max = maxValue;

            // Subscribe to max value
            max.Changed += RecalculateCurrentValue;
        }

        public override float Apply(float amount)
        {
            return Mathf.Clamp(amount, min.Amount, max.Amount);
        }
    }
}
