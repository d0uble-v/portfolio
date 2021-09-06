using System;
using System.Collections.Generic;
using UnityEngine;


namespace Sourcery.Stats
{
    [Serializable]
    public class ElasticValue : FloatingValue
    {
        protected bool locked = false;


        /// <summary>
        /// The base amount on top of which the modifiers are added. Supposed to never change.
        /// </summary>
        [SerializeField] protected float baseAmount;
        public float BaseAmount
        {
            get => baseAmount;
            protected set { baseAmount = value; }
        }


        protected List<int> modifierPriorities = new List<int>();


        public override float Amount
        {
            get => base.Amount;
            set
            {
                if (locked)
                    throw new NotSupportedException("Anchored values cannot be set directly.");
                else
                    base.Amount = value;
            }
        }


        //========== CONSTRUCTORS ==========


        /// <summary>
        /// Constructor.
        /// </summary>
        /// <param name="baseAmount"></param>
        /// <param name="stat"></param>
        public ElasticValue(float baseAmount, float currentAmount, Stat stat) : base(currentAmount, stat)
        {
            this.baseAmount = baseAmount;
            // Lock for public value editing
            locked = true;
            // Recalculate
            RecalculateAmount();
        }

        public ElasticValue(float baseAmount, Stat stat) : this(baseAmount, baseAmount, stat) { }


        //========== METHODS ==========


        /// <summary>
        /// Uses base amount setter.
        /// </summary>
        /// <param name="amount"></param>
        protected virtual void SetAmount(float amount)
        {
            base.Amount = amount;
        }


        protected void UpdatePriorities()
        {
            modifierPriorities.Clear();
            foreach (var modifier in modifiers)
            {
                if (modifierPriorities.Contains(modifier.priority)) continue;
                modifierPriorities.Add(modifier.priority);
            }
            // Ensure ascending order
            modifierPriorities.Sort();
        }


        //========== OVERRIDES ==========


        public override void RecalculateAmount()
        {
            // Reset current value to base value
            float finalAmount = baseAmount;
            // Loop over modifiers by priority
            foreach (var priority in modifierPriorities)
            {
                float stackTotal = 0f;
                Modifier lastModifier = null;
                // Calculate stack value
                foreach (var modifier in modifiers)
                {
                    if (modifier.priority != priority) continue;
                    stackTotal = modifier.CalculateStack(stackTotal, modifier.Amount);
                    lastModifier = modifier;
                }
                // Update calculated value
                finalAmount = lastModifier.CalculateFinal(finalAmount, stackTotal);
            }
            // Lastly, set the new amount
            SetAmount(finalAmount);
        }


        public override void AddModifier(Modifier modifier)
        {
            base.AddModifier(modifier);
            UpdatePriorities();
            RecalculateAmount();
        }


        public override void RemoveModifier(Modifier modifier)
        {
            base.RemoveModifier(modifier);
            UpdatePriorities();
            RecalculateAmount();
        }
    }
}