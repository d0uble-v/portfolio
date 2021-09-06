using System.Collections;
using UnityEngine;


namespace Sourcery.Stats
{
    public class TickingModifier : TempModifier
    {
        public readonly float interval;


        public TickingModifier(FloatingValue target, float amount, float duration, float interval, object origin, int priority = 0) : base(target, amount, duration, origin, priority)
        {
            if (duration != float.MaxValue && duration % interval != 0)
            {
                throw new System.ArgumentException("The duration must be divisible by the interval.");
            }
            this.interval = interval;
        }


        protected override IEnumerator Expire()
        {
            float totalTimePassed = 0f;
            while (true)
            {
                target.Amount = CalculateFinal(target.Amount, Amount);
                totalTimePassed += interval;
                Debug.Log("<color=orange>Modifier applied.</color>", target.stat.statSystem);
                if (totalTimePassed >= duration) break;
                yield return new WaitForSeconds(interval);
            }
            // Lastly, remove itself
            target.RemoveModifier(this);
        }
    }
}