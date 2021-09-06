using System;

namespace Sourcery.Stats
{
    [Serializable]
    public class ConstantValue : StatValue
    {
        protected bool locked = false;


        public override float Amount
        {
            get => base.Amount;
            set
            {
                if (locked)
                    throw new NotSupportedException("Constant values cannot be modified.");
                else
                    base.Amount = value;
            }
        }


        public ConstantValue(float amount, Stat stat) : base(amount, stat)
        {
            locked = true;
        }
    }
}