using System.Collections.ObjectModel;
using System.Collections.Generic;


namespace Sourcery.Stats
{
    [System.Serializable]
    public class SimpleValue : StatValue
    {
        public override float Amount
        {
            get => base.Amount;
            set
            {
                value = ApplyConstraints(value);
                base.Amount = value;
            }
        }


        /// <summary>
        /// The list of constraints applied to this value.
        /// </summary>
        protected List<IConstraint> constraints;

        /// <summary>
        /// The read-only list of all constraints applied to this value.
        /// </summary>
        public virtual ReadOnlyCollection<IConstraint> Constraints { get; protected set; }


        //========== CONSTRUCTORS ==========


        public SimpleValue(float amount, Stat stat) : base(amount, stat)
        {
            // Init constraints
            constraints = new List<IConstraint>();
            Constraints = new ReadOnlyCollection<IConstraint>(constraints);
        }


        //========== METHODS ==========


        /// <summary>
        /// Adds a constraint for this value.
        /// </summary>
        /// <param name="constraint"></param>
        public virtual void AddConstraint(IConstraint constraint)
        {
            constraints.Add(constraint);
            RecalculateAmount();
        }


        /// <summary>
        /// Removes a constraint for this value.
        /// </summary>
        /// <param name="constraint"></param>
        public virtual void RemoveConstraint(IConstraint constraint)
        {
            constraints.Remove(constraint);
            RecalculateAmount();
        }


        /// <summary>
        /// Recalculates current amount.
        /// </summary>
        public virtual void RecalculateAmount()
        {
            Amount = Amount;
        }


        /// <summary>
        /// Apply constraints to the amount being set.
        /// </summary>
        protected virtual float ApplyConstraints(float amount)
        {
            if (constraints != null)
            {
                foreach (var constraint in constraints)
                {
                    amount = constraint.Apply(amount);
                }
            }
            return amount;
        }
    }
}