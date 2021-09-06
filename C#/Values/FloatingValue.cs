using System.Collections.ObjectModel;
using System.Collections.Generic;


namespace Sourcery.Stats
{
    [System.Serializable]
    public class FloatingValue : SimpleValue
    {
        /// <summary>
        /// The list of all modifiers applied to this value.
        /// </summary>
        protected List<Modifier> modifiers;

        /// <summary>
        /// The read-only list of all modifiers applied to this value.
        /// </summary>
        public virtual ReadOnlyCollection<Modifier> Modifiers { get; protected set; }


        //========== CONSTRUCTORS ==========


        public FloatingValue(float amount, Stat stat) : base(amount, stat)
        {
            // Init modifiers
            modifiers = new List<Modifier>();
            Modifiers = new ReadOnlyCollection<Modifier>(modifiers);
        }


        //========== METHODS ==========


        /// <summary>
        /// Adds amount modifier and activates its custom logic.
        /// </summary>
        /// <param name="modifier"></param>
        public virtual void AddModifier(Modifier modifier)
        {
            modifiers.Add(modifier);
            modifier.Activate();
        }


        /// <summary>
        /// Removes amount modifier and deactivates its custom logic.
        /// </summary>
        /// <param name="modifier"></param>
        public virtual void RemoveModifier(Modifier modifier)
        {
            modifier.Deactivate();
            modifiers.Remove(modifier);
        }


        /// <summary>
        /// Removes amount modifier.
        /// </summary>
        /// <param name="modifier"></param>
        public virtual bool HasModifier(Modifier modifier)
        {
            if (modifiers != null)
            {
                return modifiers.Contains(modifier);
            }
            return false;
        }
    }
}