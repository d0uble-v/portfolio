using UnityEngine;

namespace Sourcery.Stats
{
    [System.Serializable]
    public abstract class StatValue
    {
        /// <summary>
        /// The parent stat of this value.
        /// </summary>
        public readonly Stat stat;


        /// <summary>
        /// The private variable that stores this value's amount.
        /// </summary>
        [SerializeField] private float amount;


        /// <summary>
        /// This value's current amount. Triggers the "changed" event if amount changed.
        /// </summary>
        public virtual float Amount
        {
            get => amount;
            set
            {
                if (amount == value) return;
                amount = value;
                Debug.Log("<color=green>" + stat.name + " amount changed to " + amount + "</color>", stat.statSystem);
                Changed?.Invoke(this);
            }
        }


        //========== EVENTS ==========


        /// <summary>
        /// The event notifying the amount has changed.
        /// </summary>
        public event System.Action<StatValue> Changed;

        public delegate void OnChanged(float value);


        //========== CONSTRUCTORS ==========


        /// <summary>
        /// The constructor.
        /// </summary>
        public StatValue(float amount, Stat stat)
        {
            // Set values
            this.stat = stat;
            Amount = amount;
        }
    }
}