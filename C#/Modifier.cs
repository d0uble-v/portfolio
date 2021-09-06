using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Sourcery.Stats
{
    public class Modifier
    {
        public readonly StatValue target;


        private float amount;
        public virtual float Amount
        {
            get => amount;
            protected set
            {
                amount = value;
            }
        }


        /// <summary>
        /// Reference to where this modifiers comes from.
        /// </summary>
        public readonly object origin;


        /// <summary>
        /// Order for stacking modifiers. The lower the priority is, the earlier this modifier will be apllied.
        /// </summary>
        public readonly int priority;


        public Modifier(StatValue target, float amount, object origin, int priority = 0)
        {
            this.target = target;
            this.amount = amount;
            this.origin = origin;
            this.priority = priority;
        }


        /// <summary>
        /// Activates custom logic. Intended to be used by stat values internally.
        /// </summary>
        public virtual void Activate() { }


        /// <summary>
        /// Deactivates custom logic. Intended to be used by stat values internally.
        /// </summary>
        public virtual void Deactivate() { }


        /// <summary>
        /// This method can be used by a stat value to stack multiple modifiers of the same kind.
        /// </summary>
        /// <param name="totalAmount"></param>
        /// <param name="changeAmount"></param>
        /// <returns></returns>
        public virtual float CalculateStack(float totalAmount, float changeAmount)
        {
            return totalAmount + changeAmount;
        }


        /// <summary>
        /// This method is used to calculate the new amount of the stat value after the modifier is applied.
        /// The stat amount and the change amount are passed separately to keep this method flexible and 
        /// usable by stat values themselves, e.g. during stacking.
        /// </summary>
        /// <param name="currentAmount"></param>
        /// <param name="changeAmount"></param>
        /// <returns></returns>
        public virtual float CalculateFinal(float currentAmount, float changeAmount)
        {
            return currentAmount + changeAmount;
        }
    }
}